import random
import threading
import time

from . import config, seed_data, websearch
from .util import top_ngrams


class AutoFeed:
    """Autonomous research loop: picks topics (learning what YOU ask about),
    searches the web, reads pages, stores knowledge, discovers sub-topics
    and retrains the brain - until stopped."""

    def __init__(self, memory, brain):
        self.mem = memory
        self.brain = brain
        self.stop_event = threading.Event()
        self.running = False
        self.interval = config.AF_INTERVAL
        self.seed_topics = list(seed_data.CURRICULUM_SEEDS)
        self.pending_passages = 0
        self.cycles = 0
        self.state = "idle"
        self.lock = threading.RLock()
        self.worker = None

    def _ensure_seed_topics(self):
        for t in self.seed_topics:
            self.mem.bump_topic(t, priority=0.42, category=seed_data.classify_category(t))

    def start_feed(self, seed_topics=None, interval=None):
        with self.lock:
            if self.running:
                return False
            self.running = True
            self.stop_event.clear()
            if seed_topics:
                self.seed_topics = [t.strip().lower() for t in seed_topics if t.strip()]
            if interval:
                self.interval = max(8.0, min(600.0, float(interval)))
            self._ensure_seed_topics()
            self.mem.add_feed("feed", "AutoFeed STARTED · interval %.0fs · %d topics queued"
                              % (self.interval, len(self.seed_topics)))
            self.worker = threading.Thread(target=self._loop, daemon=True)
            self.worker.start()
            return True

    def stop_feed(self):
        self.stop_event.set()
        with self.lock:
            self.running = False
        self.mem.add_feed("feed", "AutoFeed STOPPED by user")

    def status(self):
        return {"running": self.running, "cycles": self.cycles, "state": self.state,
                "pending_train": self.pending_passages, "interval": self.interval,
                "seed_topics": len(self.seed_topics)}

    def _loop(self):
        try:
            while not self.stop_event.is_set():
                try:
                    self.cycle()
                except Exception as e:
                    self.mem.add_feed("error", "cycle error: %r" % e)
                self.stop_event.wait(self.interval)
        finally:
            with self.lock:
                self.running = False
                self.state = "idle"

    def cycle(self):
        self.cycles += 1
        picks = self.mem.next_topics(1)
        if random.random() < 0.35 or not picks:
            t = random.choice(self.seed_topics)
            picks.append({"name": t, "category": seed_data.classify_category(t),
                          "priority": 0.5})
        for topic in picks[:2]:
            if self.stop_event.is_set():
                return
            name = topic["name"]
            cat = topic.get("category") or seed_data.classify_category(name)
            templates = seed_data.CATEGORY_QUERY_TEMPLATES.get(
                cat, seed_data.CATEGORY_QUERY_TEMPLATES["general"])
            query = random.choice(templates).replace("{t}", name)
            self.state = "searching: %s" % name
            results, status = websearch.web_search(query, n=6)
            self.mem.mark_topic_fetched(name)
            if not results:
                self.mem.add_feed("warn", "no search results for '%s'" % query[:60])
                continue
            self.mem.add_feed("feed", "researching '%s' → %d sources found"
                              % (name, len(results)))
            urls = [r["url"] for r in results]
            self.state = "reading pages about %s" % name
            pages = websearch.fetch_many(urls, workers=3,
                                         limit=config.AF_PAGES_PER_CYCLE + 1)
            added = 0
            for p in pages:
                if self.stop_event.is_set():
                    break
                ids = self.mem.add_passages(p["url"], p["title"], p["text"],
                                            source="autofeed", topic=name)
                if ids:
                    added += len(ids)
                    self._discover_subtopics(p["text"], name)
            self.pending_passages += added
            self.mem.add_feed("learn", "stored %d new passages about '%s' (pending for training: %d)"
                              % (added, name, self.pending_passages))
            with self.lock:
                self.mem.bump_topic(name, priority=0.5, category=cat)
        if self.pending_passages >= config.AF_TRAIN_EVERY:
            self.state = "training brain"
            self.mem.add_feed("train", "auto-training triggered (%d new passages)"
                              % self.pending_passages)
            self.brain.train_all(log=lambda m: self.mem.add_feed("train", m))
            self.pending_passages = 0
        self.mem.enforce_size()
        self.state = "idle"

    def _discover_subtopics(self, text, parent):
        parent = (parent or "").lower()
        for ng in top_ngrams(text, limit=6):
            ng = ng.strip()
            if 4 < len(ng) < 45 and ng != parent and not ng.isdigit():
                self.mem.bump_topic(ng, priority=0.3,
                                    category=seed_data.classify_category(ng))
        self.mem.prune_topics()
