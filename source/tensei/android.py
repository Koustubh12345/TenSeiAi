"""Android / Chaquopy integration helper.

Use TenSeiAi inside an Android app (Chaquopy bundles Python):

    // Kotlin/Java in your MainActivity (model extracted from assets first)
    String url = Python.getInstance().getModule("tensei.android")
        .callAttr("start", getFilesDir().getAbsolutePath()).toString();
    webView.loadUrl(url);

`start()` unpacks a TenSeiAi.tsei model if one is staged in the home folder
(or pass its path explicitly), boots the engine and serves the chat UI on
127.0.0.1, so an Android WebView gets the full local chat experience without
any network.  Everything runs on-device.
"""

import os
import threading


def start(home, port=8765, host="127.0.0.1", model=None):
    """Boot TenSeiAi with `home` as its data folder and serve the web chat.

    Returns the local URL (e.g. "http://127.0.0.1:8765/") as a string.
    """
    home = os.path.abspath(str(home))
    os.makedirs(home, exist_ok=True)
    os.environ["TENSEI_HOME"] = home

    from . import config, model_file
    config.ensure_dirs()

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

    from http.server import ThreadingHTTPServer
    from . import server as _server
    _server.APP = _server.App()
    srv = ThreadingHTTPServer((host, int(port)), _server.Handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return "http://%s:%d/" % (host, int(port))


def ask(home, question, model=None):
    """One-shot question inside an app (no server): returns the answer text."""
    home = os.path.abspath(str(home))
    os.makedirs(home, exist_ok=True)
    os.environ["TENSEI_HOME"] = home
    from . import config, model_file
    config.ensure_dirs()
    for name in ("TenSeiAi.tsei", "TENSEI_MODEL.tsei"):
        p = os.path.join(home, name)
        if os.path.isfile(p):
            try:
                model_file.install_model(p, home)
            except Exception:
                pass
            break
    if model:
        try:
            model_file.install_model(str(model), home)
        except Exception:
            pass
    from .memory import Memory
    from .brain import Brain
    from .thinker import Thinker
    mem = Memory()
    brain = Brain(mem)
    if brain.intent is None:
        brain.train_all()
    return Thinker(mem, brain).ask(question)["answer"]
