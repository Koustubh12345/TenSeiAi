import json
import math
import os
import random
import re
import threading
import time

from . import config, seed_data, util
from .embed import Embedder
from .lm import WordLM
from .nn import MLP
from .transmoe import TransMoE

try:
    import numpy as np
except Exception:
    np = None

W_PATH = config.BRAINS / "W.json"
INTENT_PATH = config.BRAINS / "intent.json"
SCORER_PATH = config.BRAINS / "scorer.json"
META_PATH = config.BRAINS / "meta.json"
LM_PATH = config.BRAINS / "lm.npz"
LM_VOCAB_PATH = config.BRAINS / "lm_vocab.json"
TM_PATH = config.BRAINS / "tmoe.npz"
TM_VOCAB_PATH = config.BRAINS / "tmoe_vocab.json"

INTENT_DIM = 384
SCORE_FEATS = 12


class Brain:
    """TenSeiAi's trainable core: intent MLP + relevance scorer + learned
    embedding projection. All trained from scratch on the model's own
    accumulated memory. Nothing pretrained, nothing copied."""

    def __init__(self, memory):
        self.mem = memory
        self.embedder = Embedder()
        memory.embedder = self.embedder
        self.intent = None
        self.scorer = None
        self.lm = WordLM()
        self.tmoe = None
        self.version = 0
        self.meta = {}
        self.train_lock = threading.Lock()
        self.load()
        self.ensure_origin()

    def ensure_origin(self):
        """Seed self-knowledge as normal trainable documents (not canned replies)."""
        try:
            if not self.mem.kv_get("blocked_cleanup_v1"):
                gone = self.mem.cleanup_blocked()
                self.mem.kv_set("blocked_cleanup_v1", True)
                if gone:
                    self.mem.add_feed("warn", "removed %d toxic fragments from memory" % gone)
        except Exception:
            pass
        try:
            if self.mem.kv_get("origin_seeded_v2"):
                return
            for i, fact in enumerate(seed_data.ORIGIN_FACTS):
                self.mem.add_passages("tensei://origin/%d" % i, "TenSeiAi origin facts",
                                      fact, source="origin", topic="tensei")
            self.mem.kv_set("origin_seeded_v2", True)
        except Exception:
            pass

    def load(self):
        config.ensure_dirs()
        try:
            with open(META_PATH) as f:
                self.meta = json.load(f)
        except Exception:
            self.meta = {}
        self.version = int(self.meta.get("version", 0))
        self.embedder.load(W_PATH)
        self.intent = MLP.load(INTENT_PATH)
        self.scorer = MLP.load(SCORER_PATH)
        self.lm.load(str(LM_PATH), str(LM_VOCAB_PATH))
        if isinstance(self.lm, WordLM) and self.lm.trained and not (self.lm.bi or self.lm.tri):
            try:
                self.lm.rebuild_ngrams(self._lm_texts())
            except Exception:
                pass
        # Transformer + Mixture-of-Experts generative core (TenSeiMoE). When
        # its weights exist they become THE language model; the older WordLM
        # stays as the fallback for models built before the transformer.
        try:
            tm = TransMoE()
            if tm.load(str(TM_PATH), str(TM_VOCAB_PATH)):
                self.tmoe = tm
                self.lm = tm
                if not (self.lm.bi or self.lm.tri):
                    try:
                        self.lm.rebuild_ngrams(self._lm_texts())
                    except Exception:
                        pass
        except Exception:
            pass

    def _lm_texts(self):
        """Training corpus with the self-facts heavily up-weighted, so the
        language model stays fluent about itself while learning about the
        world (otherwise millions of wiki words drown ten origin sentences)."""
        origin = []
        try:
            for d in self.mem.get_docs_by_source("origin", limit=60):
                p = d.get("passage") if isinstance(d, dict) else None
                if p:
                    origin.append(p)
        except Exception:
            pass
        texts = origin * 24
        try:
            texts.extend(self.mem.corpus_texts(limit_chars=3000000))
        except TypeError:
            texts.extend(self.mem.corpus_texts())
        try:
            from . import codesmith as _cs
            prog = [
                "a python program is written in a file ending in .py and runs with python3 file.py",
                "a bash script begins with a shebang line and is run with bash script.sh",
                "to run a c program compile it with cc main.c -o main then run ./main",
                "a javascript program runs with node app.js",
                "to write a program you choose a language create a file and write instructions",
                "programming means writing instructions that a computer follows step by step",
                "tenseiai can write programs and scripts in many languages and syntax check them",
            ]
            for lang, code in list(_cs._HELLO.items()):
                prog.append("a small %s program: %s" % (lang, " ".join(code.split())))
            for lang, code in list(_cs._FULL.items()):
                prog.append("a complete %s starter program defines a function and calls it "
                            "from main: %s" % (lang, " ".join(code.split())))
            texts.extend(prog * 6)
        except Exception:
            pass
        return texts

    def save_meta(self):
        d = dict(self.meta)
        d["version"] = self.version
        tmp = str(META_PATH) + ".tmp"
        with open(tmp, "w") as f:
            json.dump(d, f, indent=1)
        os.replace(tmp, META_PATH)
        try:
            self.mem.kv_set("brain", d)
        except Exception:
            pass

    def intent_features(self, text):
        v = [0.0] * INTENT_DIM
        ws = util.words(text)
        toks = ws + util.bigrams(ws)
        for t in toks:
            idx = util.h64(t, 7) % INTENT_DIM
            v[idx] += 1.0
        return util.nrm(v)

    def classify_intent(self, text):
        if self.intent is None:
            return "unknown", 0.0
        p = self.intent.predict_proba(self.intent_features(text))
        i = max(range(len(p)), key=lambda k: p[k])
        name = seed_data.INTENT_CLASSES[i] if i < len(seed_data.INTENT_CLASSES) else "unknown"
        return name, float(p[i])

    def scorer_features(self, query, passage):
        qw = util.content_words(query)
        pw = util.content_words(passage)
        if not qw or not pw:
            return [0.0] * SCORE_FEATS
        qset, pset = set(qw), set(pw)
        inter = qset & pset
        qbs = set(util.bigrams(qw))
        pbs = set(util.bigrams(pw))
        binter = qbs & pbs
        idf_cov = sum(self.mem.idf(t) for t in inter) / (sum(self.mem.idf(t) for t in qset) + 1e-6)
        cov = len(inter) / len(qset)
        bcov = len(binter) / max(1, len(qbs))
        jac = len(inter) / max(1, len(qset | pset))
        density = len(inter) / (1.0 + math.log(1 + len(pw)))
        first_sent = util.sentences(passage)
        f_cov = 0.0
        if first_sent:
            fw = set(util.content_words(first_sent[0]))
            f_cov = len(qset & fw) / len(qset)
        nums_q = {w for w in qw if w.isdigit()}
        nums_p = {w for w in pw if w.isdigit()}
        n_cov = len(nums_q & nums_p) / max(1, len(nums_q)) if nums_q else 0.0
        pos_bonus = 1.0 if inter and list(pset)[:20] else 0.0
        length_bucket = min(1.0, len(passage) / 1200.0)
        exact_q = 1.0 if query.lower().strip() in passage.lower() else 0.0
        return [cov, bcov, idf_cov, jac, density * 3.0, f_cov, n_cov,
                pos_bonus, length_bucket, exact_q,
                1.0 if inter else 0.0, min(1.0, len(inter) / 8.0)]

    def score_passage(self, query, passage, base_sim=0.0):
        feats = self.scorer_features(query, passage)
        lex = (feats[2] * 0.5 + feats[0] * 0.3 + feats[1] * 0.2)
        if self.scorer is not None:
            learned = self.scorer.predict_proba(feats)[0]
            return max(0.0, min(1.0, 0.45 * base_sim + 0.15 * lex + 0.40 * learned))
        return max(0.0, min(1.0, 0.65 * base_sim + 0.35 * lex))

    def train_all(self, log=None, force=False):
        log = log or (lambda s: None)
        if not self.train_lock.acquire(blocking=False):
            log("training already running, skipped")
            return self.meta
        try:
            t0 = time.time()
            ver = self.version + 1
            log("training v%d started" % ver)
            metrics = {}

            intent = self._train_intent(ver, log)
            metrics["intent"] = intent

            metrics["embed"] = self._train_embedding(ver, log)
            metrics["scorer"] = self._train_scorer(ver, log)
            metrics["lm"] = self._train_lm(log)

            self.version = ver
            self.meta = {"version": ver, "trained_at": time.time(),
                         "metrics": metrics,
                         "took_s": round(time.time() - t0, 2)}
            self.save_meta()
            self.mem.add_feed("train", "brain v%d trained in %.1fs (%s)"
                              % (ver, time.time() - t0,
                                 ", ".join("%s=%s" % (k, v.get("acc", v.get("val_acc", "?")))
                                           for k, v in metrics.items())))
            log("training v%d done in %.1fs" % (ver, time.time() - t0))
            return self.meta
        finally:
            self.train_lock.release()

    @staticmethod
    def _heuristic_intent(q):
        """Surface-form label for a stored question. Used to grow the intent
        training set from the real question log with a trustworthy signal
        (better than training on the previous model's own guesses)."""
        ql = (q or "").strip().lower()
        if not ql:
            return None
        if re.fullmatch(r"[0-9\s+\-*/().%^=]+", ql):
            return "math"
        if re.match(r"^\s*(?:solve|compute|evaluate)\b", ql) or re.search(
                r"\bhow many (?:seconds|minutes|hours|days|weeks|months|years|"
                r"metres|meters|kilometres|kilometers|miles|kg|kilograms|"
                r"pounds|litres|liters|bytes|kb|mb|gb)\b", ql) or re.search(
                r"\b\d+\s*[+\-*/^]\s*\d+", ql):
            return "math"
        if re.match(r"^\s*(?:tell me\s+|please\s+)?when\b", ql):
            return "factoid"
        if re.match(r"^\s*(?:tell me\s+|please\s+)?who\b", ql):
            return "factoid"
        if re.match(r"^\s*(?:tell me\s+|please\s+)?where\b", ql):
            return "factoid"
        if re.match(r"^\s*(?:tell me\s+|please\s+)?(?:what|which)\s+"
                    r"(?:is|are|was|were|does|do|did)\b", ql):
            return "definition"
        if re.match(r"^\s*(?:tell me\s+|please\s+)?why\b", ql):
            return "why"
        if re.match(r"^\s*(?:tell me\s+|please\s+)?how\b", ql):
            return "howto"
        if re.search(r"\bdifference between\b|\bcompare\b|\bvs\.?\b", ql):
            return "compare"
        if re.search(r"\b(latest|newest|current|today|this year|20\d\d)\b", ql):
            return "latest"
        if re.match(r"^\s*(?:hi|hello|hey|yo|howdy|good (?:morning|evening|"
                    r"afternoon|night))\b", ql):
            return "greeting"
        if re.search(r"\b(you|your)\b", ql) and re.search(
                r"\b(are|do|can|is|did|will)\b", ql):
            return "identity"
        return None

    def _augmented_intent_data(self):
        X_text, y = seed_data.generate(limit_per_class=90)
        qa = self.mem.qa_rows(limit=600)
        added = 0
        for row in qa:
            cls = self._heuristic_intent(row["question"])
            if cls is None:
                if added > 80:
                    continue
                cls, conf = self.classify_intent(row["question"])
                if conf < 0.45 and self.intent is not None:
                    continue
            if cls in seed_data.INTENT_CLASSES:
                X_text.append(row["question"])
                y.append(seed_data.INTENT_CLASSES.index(cls))
                added += 1
        return X_text, y

    def _train_intent(self, ver, log):
        X_text, y = self._augmented_intent_data()
        X = [self.intent_features(t) for t in X_text]
        m = MLP([INTENT_DIM, 64, len(seed_data.INTENT_CLASSES)], seed=ver)
        met = m.train(X, y, epochs=20, lr=0.06, l2=2e-4, batch=16, seed=ver,
                      log=None)
        m.save(INTENT_PATH)
        self.intent = m
        log("intent trained: samples=%d val_acc=%.3f" % (len(X), met.get("val_acc", 0)))
        return {"samples": len(X), "val_acc": met.get("val_acc", 0),
                "acc": met.get("val_acc", 0)}

    def _row_positives(self, row, limit=3):
        """Passages that support a QA row: the web documents it cited, or - for
        curated pack rows (teacher://, facts://) that cite no documents - the
        answer text itself, so pack knowledge also trains the embedder."""
        urls = [e.get("url") for e in (row.get("evidence") or [])
                if isinstance(e, dict)
                and (e.get("url") or "").startswith("http")]
        positives = self.mem.passages_for_urls(urls, limit=limit)
        if not positives and row.get("answer"):
            a = re.sub(r"[*`>#\s]+", " ", row["answer"]).strip()[:400]
            if len(a) >= 25:
                emb = self.embedder.encode(a)
                if emb:
                    positives = [{"id": -1, "url": "", "title": "",
                                  "passage": a, "emb": emb}]
        return positives

    def _training_pairs(self, max_pairs):
        rows = self.mem.qa_rows(limit=400)
        pairs = []
        for row in rows:
            if row["feedback"] < 0:
                continue
            if not row["emb"]:
                continue
            positives = self._row_positives(row, limit=3)
            for pos in positives:
                if pos["emb"]:
                    pairs.append((row["question"], pos["emb"], pos["id"]))
        rnd = random.Random(7)
        rnd.shuffle(pairs)
        pairs = pairs[:max_pairs]
        out = []
        for q, pos_emb, pos_id in pairs:
            negs = self.mem.random_passages(1, exclude_ids=[pos_id])
            if not negs or not negs[0]["emb"]:
                continue
            out.append((q, pos_emb, negs[0]["emb"]))
        return out

    def _train_embedding(self, ver, log):
        cap = 1200 if np is not None else 150
        pairs = self._training_pairs(cap)
        if not pairs:
            log("embedding: not enough Q&A evidence yet, skipped")
            return {"pairs": 0, "acc": "n/a"}
        d = self.embedder.dim
        self.embedder.init_W_identity()
        acc = 0.0
        if np is None:
            acc = self._train_embedding_py(pairs, d, ver, log)
            return {"pairs": len(pairs), "acc": acc}
        W = np.asarray(self.embedder.W, dtype=np.float64).reshape(d, d)
        rnd = random.Random(ver)
        rnd.shuffle(pairs)
        lr = 0.02
        margin = 0.25
        for epoch in range(3):
            correct = 0
            for q, pos, neg in pairs:
                xq = np.asarray(self.embedder.base_encode(q), dtype=np.float64)
                y = W @ xq
                ny = float(np.linalg.norm(y)) + 1e-9
                yhat = y / ny
                s_pos = float(yhat @ np.asarray(pos))
                s_neg = float(yhat @ np.asarray(neg))
                if s_pos > s_neg:
                    correct += 1
                if margin - s_pos + s_neg > 0:
                    dl = np.asarray(neg, dtype=np.float64) - np.asarray(pos, dtype=np.float64)
                    dl = (dl - float(dl @ yhat) * yhat) / ny
                    W -= lr * np.outer(dl, xq)
            fn = float(np.linalg.norm(W)) + 1e-9
            W *= math.sqrt(d) / fn
        self.embedder.W = W.reshape(-1).tolist()
        self.embedder._Wnp = None
        self.embedder.save(W_PATH)
        acc = round(correct / max(1, len(pairs)), 3)
        log("embedding projection trained: pairs=%d pair_acc=%.3f" % (len(pairs), acc))
        return {"pairs": len(pairs), "acc": acc}

    def _train_embedding_py(self, pairs, d, ver, log):
        Wm = [float(x) for x in self.embedder.W]
        Wm = [Wm[i * d:(i + 1) * d] for i in range(d)]
        lr = 0.02
        margin = 0.25
        correct = 0
        for epoch in range(2):
            correct = 0
            for q, pos, neg in pairs:
                xq = self.embedder.base_encode(q)
                y = [sum(wj * xj for wj, xj in zip(row, xq)) for row in Wm]
                ny = math.sqrt(sum(v * v for v in y)) + 1e-9
                yhat = [v / ny for v in y]
                s_pos = sum(a * b for a, b in zip(yhat, pos))
                s_neg = sum(a * b for a, b in zip(yhat, neg))
                if s_pos > s_neg:
                    correct += 1
                if margin - s_pos + s_neg > 0:
                    dl = [b - a for a, b in zip(pos, neg)]
                    proj = sum(a * b for a, b in zip(dl, yhat))
                    dy = [(dl[i] - proj * yhat[i]) / ny for i in range(d)]
                    for i in range(d):
                        dyi = dy[i]
                        row = Wm[i]
                        for j in range(d):
                            row[j] -= lr * dyi * xq[j]
        fro = math.sqrt(sum(v * v for row in Wm for v in row)) + 1e-9
        sc = math.sqrt(d) / fro
        flat = [v * sc for row in Wm for v in row]
        self.embedder.W = flat
        self.embedder._Wnp = None
        self.embedder.save(W_PATH)
        acc = round(correct / max(1, len(pairs)), 3)
        log("embedding projection trained (python): pairs=%d pair_acc=%.3f"
            % (len(pairs), acc))
        return acc

    def _train_lm(self, log):
        """Language-model stage: TenSeiMoE (Transformer + Mixture-of-Experts)
        is the generative core, trained by tools/train_tmoe.py.  Retraining the
        whole transformer on every brain refresh would take ~20 minutes, so
        train_all only reports its current state; use the tool to (re)train or
        fine-tune it.  The older WordLM still trains if no transformer exists."""
        try:
            if isinstance(self.lm, TransMoE):
                met = dict(self.lm.metrics or {})
                if met:
                    log("transformer-moe language model active: params=%d ppl=%s "
                        "vocab=%d (retrain: tools/train_tmoe.py)"
                        % (self.lm.param_count(), met.get("ppl", "?"), self.lm.V))
                    return met
                log("transformer-moe present but untrained; run tools/train_tmoe.py")
                return {"samples": 0, "acc": "n/a"}
            texts = self._lm_texts()
            met = self.lm.train(texts, epochs=4, log=None)
            if met:
                self.lm.save(str(LM_PATH), str(LM_VOCAB_PATH))
                log("language model trained: vocab=%d samples=%d loss=%.3f ppl=%.1f"
                    % (met.get("vocab", 0), met.get("samples", 0),
                       met.get("loss", 0), met.get("ppl", 0)))
                return met
            log("language model: needs more knowledge before it can speak")
            return {"samples": 0, "acc": "n/a"}
        except Exception as e:
            log("language model training failed: %r" % e)
            return {"acc": "n/a"}

    def _train_scorer(self, ver, log):
        rows = self.mem.qa_rows(limit=250)
        X, y = [], []
        for row in rows:
            positives = self._row_positives(row, limit=2)
            for pos in positives:
                X.append(self.scorer_features(row["question"], pos["passage"]))
                y.append(1)
                negs = self.mem.random_passages(1, exclude_ids=[pos["id"]])
                if negs:
                    X.append(self.scorer_features(row["question"], negs[0]["passage"]))
                    y.append(0)
        if len(X) < 12:
            log("scorer: not enough data yet, skipped")
            return {"samples": len(X), "acc": "n/a"}
        m = MLP([SCORE_FEATS, 16, 1], seed=ver + 100, out_act="sigmoid")
        vf = 0.2 if len(X) >= 40 else 0.0
        met = m.train(X, y, epochs=25, lr=0.08, l2=2e-4, batch=8, seed=ver,
                      val_frac=vf, log=None)
        m.save(SCORER_PATH)
        self.scorer = m
        log("relevance scorer trained: samples=%d acc=%.3f"
            % (len(X), met.get("train_acc", 0)))
        return {"samples": len(X), "val_acc": met.get("val_acc", 0),
                "acc": met.get("train_acc", met.get("val_acc", 0))}
