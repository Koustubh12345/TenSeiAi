"""Native Android bridge for TenSeiAi.

Provides JSON-friendly calls to the native Android UI via Chaquopy.
Enables hybrid offline/online intelligence: local fast inference with
automatic live web research when connected to the internet.
"""

import json
import os
import ssl
import threading
import time
import traceback
from threading import RLock

_LOCK = RLock()
_ENGINE = None
_HOME = None
_MODEL = None
_READY_AT = 0

# Set unverified SSL context fallback for Android environment
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except Exception:
    pass


def _json(payload):
    return json.dumps(payload, ensure_ascii=False)


def initialize(home, model=None):
    """Boot the local engine once and return a JSON status document."""
    global _ENGINE, _HOME, _MODEL, _READY_AT
    home = os.path.abspath(str(home))
    with _LOCK:
        if _ENGINE is not None:
            return _json({
                "ok": True,
                "reused": True,
                "version": getattr(_ENGINE, "version", "8.1.0"),
                "mode": "hybrid"
            })

        _HOME = home
        os.makedirs(home, exist_ok=True)
        os.environ["TENSEI_HOME"] = home
        # Enable hybrid / online web search by default
        os.environ["TENSEI_OFFLINE"] = "0"
        os.environ["TENSEI_RESEARCH"] = "auto"

        cacert = os.path.join(home, "cacert.pem")
        if os.path.isfile(cacert):
            os.environ["SSL_CERT_FILE"] = cacert

        from . import config, model_file
        config.ensure_dirs()

        # Look for model
        cands = []
        if model:
            cands.append(str(model))
        for name in ("TenSeiAi.tsei", "TenSeiAi.pyz", "TENSEI_MODEL.tsei", "model.tsei"):
            cands.append(os.path.join(home, name))
            cands.append(os.path.join(os.path.dirname(__file__), name))

        for p in cands:
            if p and os.path.isfile(p):
                try:
                    if p.endswith(".pyz"):
                        import zipfile
                        with zipfile.ZipFile(p) as zf:
                            if "TENSEI_MODEL.tsei" in zf.namelist():
                                tmp = os.path.join(home, "TENSEI_MODEL.extracted.tsei")
                                with open(tmp, "wb") as f_out:
                                    f_out.write(zf.read("TENSEI_MODEL.tsei"))
                                model_file.install_model(tmp, home)
                                try:
                                    os.unlink(tmp)
                                except Exception:
                                    pass
                                break
                    else:
                        model_file.install_model(p, home)
                        break
                except Exception:
                    pass

        from .memory import Memory
        from .brain import Brain
        from .thinker import Thinker

        started = time.time()
        mem = Memory()
        brain = Brain(mem)
        if brain.intent is None:
            brain.train_all()
        _ENGINE = Thinker(mem, brain)
        _READY_AT = time.time()

        return _json({
            "ok": True,
            "reused": False,
            "installed": True,
            "version": getattr(_ENGINE, "version", "8.1.0"),
            "boot_s": round(_READY_AT - started, 3),
            "mode": "hybrid"
        })


def status():
    """Small status document used by the native status pill."""
    with _LOCK:
        return _json({
            "ok": _ENGINE is not None,
            "version": "8.1.0",
            "home": _HOME,
            "ready_at": _READY_AT,
            "mode": "hybrid"
        })


def ask(question):
    """Answer one question through the persistent engine."""
    started = time.time()
    q = str(question or "").strip()
    if not q:
        return _json({"ok": False, "error": "Empty question"})
    if _ENGINE is None:
        return _json({"ok": False, "error": "TenSeiAi is still starting"})

    # Ensure online / web search is enabled for current queries
    os.environ["TENSEI_OFFLINE"] = "0"

    try:
        res = _ENGINE.ask(q)
        answer = res.get("answer", "")
        mode = res.get("mode", "memory")
        confidence = res.get("confidence", 0.0)
        took_s = round(time.time() - started, 2)
        raw_sources = res.get("sources", [])
        sources = []
        for s in raw_sources[:8]:
            if isinstance(s, dict):
                sources.append({"title": s.get("title", ""), "url": s.get("url", "")})
            else:
                sources.append({"title": str(s), "url": ""})

        return _json({
            "ok": True,
            "answer": answer,
            "mode": mode,
            "confidence": confidence,
            "took_s": took_s,
            "sources": sources
        })
    except Exception as exc:
        traceback.print_exc()
        return _json({
            "ok": False,
            "error": type(exc).__name__ + ": " + str(exc),
            "took_s": round(time.time() - started, 2)
        })


def close():
    """Best-effort cleanup used when the Activity is destroyed."""
    global _ENGINE, _HOME, _MODEL, _READY_AT
    with _LOCK:
        _ENGINE = None
        _HOME = None
        _MODEL = None
        _READY_AT = 0
