import json
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import config

APP = None

class App:
    def __init__(self):
        from .memory import Memory
        from .brain import Brain
        from .thinker import Thinker
        from .autofeed import AutoFeed

        config.ensure_dirs()
        self.mem = Memory()
        self.brain = Brain(self.mem)
        self.thinker = Thinker(self.mem, self.brain)
        self.feed = AutoFeed(self.mem, self.brain)
        self.jobs = {}
        self.lock = threading.Lock()
        self.started = time.time()
        if self.brain.intent is None or self.brain.version == 0:
            threading.Thread(target=self._first_boot, daemon=True).start()

    def _first_boot(self):
        self.mem.add_feed("train", "first boot: training brain from scratch")
        self.brain.train_all(log=lambda m: self.mem.add_feed("train", m))

    def submit_ask(self, q):
        jid = uuid.uuid4().hex[:12]
        with self.lock:
            self.jobs[jid] = {"status": "running", "steps": [], "result": None,
                              "q": q, "t0": time.time()}
            if len(self.jobs) > 80:
                old = sorted(self.jobs.items(), key=lambda kv: kv[1]["t0"])[:40]
                for k, _ in old:
                    self.jobs.pop(k, None)

        def run():
            try:
                res = self.thinker.ask(
                    q, progress=lambda s: self.jobs[jid]["steps"].append(s))
                with self.lock:
                    self.jobs[jid]["result"] = res
                    self.jobs[jid]["status"] = "done"
            except Exception as e:
                with self.lock:
                    self.jobs[jid]["status"] = "error"
                    self.jobs[jid]["result"] = {
                        "answer": "**internal error:** %s" % e, "steps": [],
                        "sources": [], "confidence": 0}

        threading.Thread(target=run, daemon=True).start()
        return jid

    def stats(self):
        s = dict(self.mem.stats())
        s["brain"] = self.brain.meta or {"version": 0}
        s["autofeed"] = self.feed.status()
        s["uptime_s"] = int(time.time() - self.started)
        s["name"] = "TenSeiAi"
        return s

class Handler(BaseHTTPRequestHandler):
    server_version = "TenSeiAi/8.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return {}

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        u = urlparse(self.path)
        qs = parse_qs(u.query)
        if u.path in ("/", "/index.html", "/chat"):
            self._serve_ui()
        elif u.path == "/api/stats":
            self._json(APP.stats())
        elif u.path == "/api/job":
            jid = (qs.get("id") or [""])[0]
            job = APP.jobs.get(jid)
            if not job:
                self._json({"error": "not found"}, 404)
            else:
                self._json({"status": job["status"], "steps": job["steps"],
                            "result": job["result"]})
        elif u.path == "/api/feed":
            since = int((qs.get("since") or ["0"])[0] or 0)
            self._json({"events": APP.mem.feed_since(since)})
        elif u.path == "/api/topics":
            self._json({"topics": APP.mem.all_topics(80)})
        elif u.path == "/v1/models":
            self._json({"object": "list", "data": [
                {"id": "tensei-1", "object": "model", "created": int(APP.started),
                 "owned_by": "tensei"}]})
        else:
            self._json({"error": "not found"}, 404)

    def _serve_ui(self):
        path = config.WEB / "index.html"
        try:
            body = path.read_bytes()
        except Exception:
            body = (b'{"info":"TenSeiAi API server (no web UI in this '
                    b'model file)","endpoints":["/api/ask","/api/job?id=",'
                    b'"/v1/chat/completions","/v1/models"]}')
        self.send_response(200)
        ctype = ("text/html; charset=utf-8"
                 if body[:1] not in (b"{",) else "application/json")
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        u = urlparse(self.path)
        d = self._read_json()
        if u.path == "/api/ask":
            q = (d.get("q") or d.get("question") or "").strip()
            if not q:
                self._json({"error": "empty question"}, 400)
                return
            if d.get("wait") or (d.get("question") and not d.get("async")):
                try:
                    res = APP.thinker.ask(q)
                except Exception as e:
                    self._json({"error": "internal error: %s" % e}, 500)
                    return
                self._json({
                    "answer": res.get("answer", ""),
                    "steps": res.get("steps", []),
                    "sources": res.get("sources", []),
                    "mode": res.get("mode", ""),
                    "confidence": res.get("confidence", 0),
                    "took_s": res.get("took_s", 0),
                })
            else:
                self._json({"id": APP.submit_ask(q)})
        elif u.path == "/api/feedback":
            try:
                APP.mem.set_feedback(int(d.get("qa_id")), int(d.get("rating")))
                self._json({"ok": True})
            except Exception as e:
                self._json({"error": str(e)}, 400)
        elif u.path == "/api/autofeed":
            action = d.get("action")
            if action == "start":
                topics = d.get("topics") or None
                started = APP.feed.start_feed(seed_topics=topics,
                                              interval=d.get("interval"))
                self._json({"ok": started, **APP.feed.status()})
            elif action == "stop":
                APP.feed.stop_feed()
                self._json({"ok": True, **APP.feed.status()})
            else:
                self._json({"error": "unknown action"}, 400)
        elif u.path == "/api/train":
            threading.Thread(
                target=APP.brain.train_all,
                kwargs={"log": lambda m: APP.mem.add_feed("train", m)},
                daemon=True).start()
            self._json({"ok": True, "started": True})
        elif u.path == "/v1/chat/completions":
            msgs = d.get("messages") or []
            q = ""
            for m in reversed(msgs):
                if m.get("role") == "user":
                    q = m.get("content") or ""
                    break
            if not q:
                self._json({"error": {"message": "no user message"}}, 400)
                return
            res = APP.thinker.ask(q)
            self._json({
                "id": "chatcmpl-" + uuid.uuid4().hex[:20],
                "object": "chat.completion",
                "created": int(time.time()),
                "model": d.get("model") or "tensei-1",
                "choices": [{"index": 0, "finish_reason": "stop",
                             "message": {"role": "assistant", "content": res["answer"]}}],
                "usage": {"prompt_tokens": len(q.split()),
                          "completion_tokens": len(res["answer"].split()),
                          "total_tokens": len(q.split()) + len(res["answer"].split())},
            })
        else:
            self._json({"error": "not found"}, 404)

def main(host=None, port=None):
    global APP
    config.ensure_dirs()
    APP = App()
    host = host or config.HOST
    port = int(port or config.PORT)
    srv = ThreadingHTTPServer((host, port), Handler)
    srv.daemon_threads = True
    from .cli import (banner as _banner, _col, _params_label,
                      TEAL, DIM, BOLD)
    print(_banner(), flush=True)
    print(flush=True)
    print("  " + _col("TenSeiAi", BOLD) + " " +
          _col("v%d" % APP.brain.version, TEAL) +
          "  " + _col("CORE", DIM) + " " + _col("MoE-RAG", TEAL) +
          "  " + _col("PARAMS", DIM) + " " +
          _col(_params_label(APP.brain), TEAL), flush=True)
    print("  " + _col("Chat UI", DIM) +
          "  http://%s:%d/" % (host, port), flush=True)
    print("  " + _col("API    ", DIM) +
          "  http://%s:%d/v1/chat/completions  (OpenAI-compatible)"
          % (host, port), flush=True)
    print("  " + _col("Stop   ", DIM) + "  Ctrl+C\n", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nTenSeiAi stopped.")

if __name__ == "__main__":
    import argparse
    import os
    import sys
    _ap = argparse.ArgumentParser(prog="tensei.server")
    _ap.add_argument("--host", default=None)
    _ap.add_argument("--port", default=None, type=int)
    _ap.add_argument("--model", default=None)
    _a = _ap.parse_args()
    if _a.model:
        _args = [sys.executable, "-m", "tensei", "run", "--model", _a.model]
        if _a.host:
            _args += ["--host", _a.host]
        if _a.port:
            _args += ["--port", str(_a.port)]
        os.execv(sys.executable, _args)
    main(_a.host, _a.port)
