import argparse
import os
import re
import sys
import time

_ANSI = None

def _ansi_ok():
    """True when it is safe to emit ANSI colour: an interactive terminal and
    no NO_COLOR in the environment.  Enables VT processing on Windows
    consoles the first time it is called."""
    global _ANSI
    if _ANSI is None:
        _ANSI = False
        try:
            if not os.environ.get("NO_COLOR") and sys.stdout.isatty():
                if os.name == "nt":
                    import ctypes
                    k = ctypes.windll.kernel32
                    k.SetConsoleMode(k.GetStdHandle(-11), 7)
                _ANSI = True
        except Exception:
            _ANSI = False
    return _ANSI

def _col(txt, code):
    """Wrap text in an ANSI SGR code - or return it untouched when colour
    is off, so piped output stays clean."""
    try:
        if _ansi_ok():
            return "\x1b[%sm%s\x1b[0m" % (code, txt)
    except Exception:
        pass
    return txt

CYAN = "38;5;51"
TEAL = "38;5;43"
TEAL_D = "38;5;37"
DIM = "2;37"
BOLD = "1;97"

_TENSEI_ASCII = (
    r"  _____          ____       _      _    _ ",
    r" |_   _|__ _ __ / ___|  ___(_)    / \  (_)",
    r"   | |/ _ \ '_ \\___ \ / _ \ |   / _ \ | |",
    r"   | |  __/ | | |___) |  __/ |  / ___ \| |",
    r"   |_|\___|_| |_|____/ \___|_| /_/   \_\_|",
)
_T_COLS = ("38;5;51", "38;5;45", "38;5;43", "38;5;37", "38;5;36")

def banner():
    """TenSeiAi wordmark banner in cyan-to-teal ANSI gradient."""
    out = []
    for i, g in enumerate(_TENSEI_ASCII):
        out.append("  " + _col(g, _T_COLS[i]))
    return "\n".join(out)

def _anim_ok():
    """Animations are for real interactive terminals only."""
    if not _ansi_ok():
        return False
    return os.environ.get("TENSEI_NO_ANIM", "").lower() not in (
        "1", "true", "yes", "on")

def print_banner(animated=False):
    """Print the wordmark, optionally revealing it line by line."""
    if not animated or not _anim_ok():
        print(banner(), flush=True)
        return
    for i, g in enumerate(_TENSEI_ASCII):
        print("  " + _col(g, _T_COLS[i]), flush=True)
        time.sleep(0.035)
    print("  " + _col("-" * 47, TEAL_D), flush=True)

def _fmt_took(seconds):
    """Format a measured latency the way the web UI shows it."""
    try:
        s = float(seconds)
    except Exception:
        return "0.00s"
    return ("%.2fs" % s) if s < 1 else ("%.1fs" % s)

def _quick_version():
    try:
        from . import config
        import json as _json
        meta = _json.loads((config.BRAINS / "meta.json").read_text(encoding="utf-8"))
        return str(meta.get("version", "1"))
    except Exception:
        return "1"

def _quick_params():
    try:
        from . import config
        import json as _json
        meta = _json.loads((config.BRAINS / "meta.json").read_text(encoding="utf-8"))
        n = int(((meta.get("metrics") or {}).get("lm") or {}).get("params") or 0)
        if n >= 1_000_000:
            return "~%.2fM" % (n / 1_000_000.0)
        if n > 0:
            return "~%s" % format(n, ",")
    except Exception:
        pass
    return "~?"

def _boot(animate=False):
    from . import config
    from .memory import Memory
    from .brain import Brain
    from .thinker import Thinker
    from .autofeed import AutoFeed
    config.ensure_dirs()

    spinner = None
    if animate and _anim_ok():
        import threading
        stop = threading.Event()
        frames = "\u280b\u2819\u2839\u2838\u283c\u2834\u2826\u2827\u2807\u280f"
        labels = ("linking core", "loading memory", "warming experts")
        state = {"printed": False}

        def spin():
            time.sleep(0.18)
            i = 0
            while not stop.is_set():
                label = labels[min(i // 9, len(labels) - 1)]
                sys.stdout.write("\r  " + _col(frames[i % len(frames)], TEAL) +
                                 " " + _col(label.ljust(18), DIM))
                sys.stdout.flush()
                state["printed"] = True
                i += 1
                time.sleep(0.075)

        thread = threading.Thread(target=spin, daemon=True)
        thread.start()
        spinner = (stop, thread, state)

    try:
        mem = Memory()
        brain = Brain(mem)
    finally:
        if spinner:
            stop, thread, state = spinner
            stop.set()
            thread.join(timeout=0.4)
            if state["printed"]:
                sys.stdout.write("\r\x1b[K")
                sys.stdout.flush()

    return mem, brain, Thinker(mem, brain), AutoFeed(mem, brain)

def _install_model(path):
    """Attach an external .tsei model file: unpack it into a runtime home and
    point TENSEI_HOME there.  This is what makes a shared model file work:
        python TenSeiAi.pyz chat --model /path/to/TenSeiAi.tsei"""
    from pathlib import Path
    mp = Path(path).expanduser()
    if not mp.exists():
        raise SystemExit("model file not found: %s" % mp)
    home = os.environ.get("TENSEI_HOME") or str(
        mp.resolve().parent / (mp.name + ".runtime"))
    try:
        Path(home).mkdir(parents=True, exist_ok=True)
    except Exception:
        home = str(Path.home() / ".tensei_ai")
        Path(home).mkdir(parents=True, exist_ok=True)
    os.environ["TENSEI_HOME"] = home
    from . import model_file
    info = model_file.install_model(mp, home)
    state = "unpacked" if info.get("installed") else "already installed"
    print(_col("[TenSeiAi]", TEAL) + " model %s -> %s (%s)"
          % (mp.name, home, state))
    return info

def _params_label(brain):
    """Show the packaged model's real parameter count, never a guess."""
    try:
        n = int(brain.lm.param_count())
    except Exception:
        try:
            n = int((brain.meta.get("metrics") or {}).get("lm", {}).get("params") or 0)
        except Exception:
            n = 0
    if n >= 1_000_000:
        return "~%.2fM" % (n / 1_000_000.0)
    if n > 0:
        return "~%s" % format(n, ",")
    return "~?"

def _strip_md(text):
    """Render markdown-flavoured answers as clean terminal text: no ** bold
    markers, no backticks, no fence lines, no 'Answer:' label - just readable
    paragraphs and plain code blocks."""
    if not text:
        return text
    out = []
    in_code = False
    for ln in text.split("\n"):
        if ln.strip().startswith("```"):
            in_code = not in_code
            out.append("")
            continue
        if in_code:
            out.append("    " + ln if ln.strip() else "")
            continue
        s = ln
        if len(s.strip()) >= 3 and set(s.strip()) in ({"-"}, {"="}):
            out.append("")
            continue
        s = re.sub(r"^\s{0,3}#{1,6}\s+", "", s)
        s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
        s = re.sub(r"__([^_\n]+)__", r"\1", s)
        s = re.sub(r"(?<![\w*])\*([^*\n]+?)\*(?![\w*])", r"\1", s)
        s = re.sub(r"(?<![\w_])_([^_\n]+?)_(?![\w_])", r"\1", s)
        s = re.sub(r"`([^`\n]+)`", r"\1", s)
        s = re.sub(r"^(\s*)[-*•]\s+", r"\1• ", s)
        out.append(s)
    txt = "\n".join(out)
    txt = re.sub(r"^(?:\*\*)?Answer:\s*(?:\*\*)?\s*", "", txt, flags=re.I)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return txt.strip()

def cmd_ask(args):
    import json as _json
    if getattr(args, "model", None):
        _install_model(args.model)
    if getattr(args, "offline", False):
        os.environ["TENSEI_OFFLINE"] = "1"
    mem, brain, think, feed = _boot()
    verbose = getattr(args, "verbose", False)
    q = (args.question or "").strip()
    if not q or q == "-":
        try:
            q = sys.stdin.read().strip()
        except Exception:
            q = ""
    if not q:
        print('usage: TenSeiAi.pyz ask "your question"  '
              '(or: echo "question" | TenSeiAi.pyz ask -)', file=sys.stderr)
        return 2
    if brain.intent is None:
        if verbose:
            brain.train_all(log=lambda m: print(" [train]", m, file=sys.stderr))
        else:
            brain.train_all()

    def _prog(s):
        if verbose:
            print(" [%.1fs] %s" % (s["t"], s["msg"]), file=sys.stderr)

    res = think.ask(q, progress=_prog)
    if getattr(args, "json", False):
        print(_json.dumps({"question": q, "answer": res["answer"],
                           "mode": res["mode"],
                           "confidence": res["confidence"],
                           "took_s": res["took_s"]}))
    else:
        ans = res["answer"]
        try:
            if sys.stdout.isatty():
                ans = _strip_md(ans)
        except Exception:
            pass
        print(ans)
        if verbose:
            print("(mode=%s confidence=%.0f%% took=%.1fs)"
                  % (res["mode"], res["confidence"] * 100, res["took_s"]),
                  file=sys.stderr)
    return 0

BANNER = banner()

CHAT_HELP = """commands:
  /help          show this help
  /steps on|off  show or hide the thinking/research steps (default: off)
  /stats         show memory + brain statistics
  /web on|off    toggle live internet research
  /train         (re)train the small brain networks (intent/scorer/embedding)
  /feed on|off   toggle the background AutoFeed learner
  /exit          quit (or Ctrl+C)
"""

def cmd_chat(args):
    if getattr(args, "model", None):
        _install_model(args.model)
    if getattr(args, "offline", False):
        os.environ["TENSEI_OFFLINE"] = "1"
    mem, brain, think, feed = _boot(animate=True)
    if brain.intent is None:
        print("first boot: training brain...")
        brain.train_all(log=lambda m: print(" [train]", m))
    print_banner(animated=True)
    print()
    print("  " + _col("TenSeiAi", BOLD) + " " +
          _col("v%s" % brain.meta.get("version", "?"), TEAL))
    print("  " + _col("CORE", DIM) + "    " + _col("MoE-RAG", TEAL) +
          "    " + _col("PARAMS", DIM) + "  " + _col(_params_label(brain), TEAL))
    print("  " + _col("type a question", DIM) + " - " +
          _col("/help", TEAL) + " for commands, " + _col("/exit", TEAL) + " to quit\n")
    steps_on = bool(getattr(args, "steps", False))
    while True:
        try:
            q = input(_col("you", TEAL) + _col("> ", DIM)).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not q:
            continue
        low = q.lower()
        if low in ("exit", "quit", "/exit", "/quit"):
            break
        if low in ("/help", "help", "?"):
            print(CHAT_HELP)
            continue
        if low == "/stats":
            try:
                import json as _json
                print(_json.dumps({"memory": mem.stats(), "brain_version": brain.meta.get("version"),
                                   "metrics": brain.meta.get("metrics", {})}, indent=2)[:2000])
            except Exception as e:
                print("stats failed:", e)
            continue
        if low.startswith("/steps"):
            if "on" in low:
                steps_on = True
            elif "off" in low:
                steps_on = False
            else:
                steps_on = not steps_on
            print("[thinking steps %s]" % ("on" if steps_on else "off"))
            continue
        if low.startswith("/web"):
            os.environ["TENSEI_OFFLINE"] = "0" if "on" in low else "1"
            print("[web research %s]" % ("on" if os.environ.get("TENSEI_OFFLINE") == "0" else "off"))
            continue
        if low.startswith("/feed") or q.startswith("!feed"):
            if "on" in low:
                feed.start_feed()
                print("[autofeed started]")
            else:
                feed.stop_feed()
                print("[autofeed stopped]")
            continue
        if low == "/train":
            print("[training...]")
            meta = brain.train_all(log=lambda m: print("  [train]", m))
            print("[done] v%s" % meta.get("version"))
            continue
        if steps_on:
            res = think.ask(q, progress=lambda s: print("  [%.1fs] %s" % (s["t"], s["msg"])))
        else:
            res = think.ask(q)
        print()
        print(_strip_md(res["answer"]))
        print("\n  " + _col("Took %s" % _fmt_took(res.get("took_s", 0)), DIM))
        if steps_on:
            m = res.get("mode", "")
            if m and m not in ("memory", "learned"):
                print("  " + _col("(%s, confidence %.0f%%)"
                                  % (m, res.get("confidence", 0) * 100), DIM))
        print()

def _serve_with_browser(args):
    """Start the local web chat and open the browser on it (Termux-aware)."""
    import threading
    import webbrowser
    from . import config
    host = getattr(args, "host", None) or config.HOST
    port = int(getattr(args, "port", None) or config.PORT)
    shown = "127.0.0.1" if host in ("0.0.0.0", "::", "") else host
    url = "http://%s:%d/" % (shown, port)

    def _open():
        import socket
        probe_host = "127.0.0.1" if shown in ("0.0.0.0", "::", "") else shown
        deadline = time.time() + 60
        while time.time() < deadline:
            try:
                with socket.create_connection((probe_host, port), timeout=0.5):
                    break
            except OSError:
                time.sleep(0.25)
        if os.environ.get("TERMUX_VERSION"):
            try:
                import subprocess
                subprocess.Popen(["termux-open-url", url])
                return
            except Exception:
                pass
        try:
            webbrowser.open(url)
        except Exception:
            pass

    threading.Thread(target=_open, daemon=True).start()
    print("\n  " + _col("web chat", DIM) + "  " + _col(url, TEAL) +
          _col("  (starting the local server, opening your browser...)", DIM) + "\n")
    from .server import main as serve
    serve(host, port)
    return 0

def cmd_launch(args):
    """Launcher screen: pick terminal chat or the browser chat UI."""
    if getattr(args, "model", None):
        _install_model(args.model)
        args.model = None
    if getattr(args, "offline", False):
        os.environ["TENSEI_OFFLINE"] = "1"
    try:
        interactive = sys.stdin.isatty()
    except Exception:
        interactive = False
    if not interactive and os.environ.get("TENSEI_FORCE_MENU") != "1":
        return cmd_chat(args)
    print_banner(animated=True)
    print()
    print("  " + _col("TenSeiAi", BOLD) + " " + _col("v%s" % _quick_version(), TEAL))
    print("  " + _col("CORE", DIM) + "    " + _col("MoE-RAG", TEAL) +
          "    " + _col("PARAMS", DIM) + "  " + _col(_quick_params(), TEAL))
    print()
    print("  " + _col("How do you want to chat?", DIM))
    print()
    print("    " + _col("1", TEAL) + "  Terminal chat      " +
          _col("right here in this window", DIM))
    print("    " + _col("2", TEAL) + "  Web chat           " +
          _col("opens in your browser", DIM))
    print("    " + _col("q", TEAL) + "  Quit")
    print()
    choice = ""
    for _ in range(6):
        try:
            choice = input("  choose " + _col("[1]", TEAL) + ": ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            choice = "q"
        if not choice:
            choice = "1"
        if choice in ("1", "2", "q", "quit", "exit"):
            break
        print("  please type 1, 2 or q")
    if choice in ("q", "quit", "exit"):
        return 0
    if choice == "2":
        return _serve_with_browser(args)
    return cmd_chat(args)

def cmd_feed(args):
    mem, brain, think, feed = _boot()
    if brain.intent is None:
        print("first boot: training brain...")
        brain.train_all(log=lambda m: print(" [train]", m))
    topics = [t.strip() for t in args.topics.split(",")] if args.topics else None
    feed.start_feed(seed_topics=topics, interval=args.interval)
    print("AutoFeed running. Ctrl+C to stop.")
    seen = 0
    try:
        while True:
            ev = mem.feed_since(seen)
            for e in ev:
                print("  [%s] %s" % (e["kind"], e["msg"]))
                seen = max(seen, e["id"])
            time.sleep(1.5)
    except KeyboardInterrupt:
        feed.stop_feed()
        print("\nAutoFeed stopped.")
        print("stats:", mem.stats())

def cmd_bridge(args):
    """Line-JSON bridge for host apps (Android APK, editors, bots):
    reads {"q": "..."} lines on stdin, writes {"answer": ...} lines on stdout."""
    import json as _json
    mem, brain, think, feed = _boot()
    if brain.intent is None:
        brain.train_all(log=lambda m: print(" [train]", m, file=sys.stderr))
    sys.stdout.write(_json.dumps({
        "ok": True, "ready": True, "name": "TenSeiAi",
        "version": brain.meta.get("version")}) + "\n")
    sys.stdout.flush()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = _json.loads(line)
            q = str(req.get("q") or req.get("question") or "").strip()
            if not q:
                raise ValueError("empty question")
            res = think.ask(q)
            out = {"answer": res["answer"], "mode": res["mode"],
                   "confidence": res["confidence"], "took_s": res["took_s"]}
        except Exception as e:
            out = {"error": "%s: %s" % (type(e).__name__, e)}
        sys.stdout.write(_json.dumps(out) + "\n")
        sys.stdout.flush()
    return 0

def cmd_train(args):
    mem, brain, think, feed = _boot()
    meta = brain.train_all(log=lambda m: print(" [train]", m))
    print("brain version:", meta.get("version"), "metrics:", meta.get("metrics"))

def cmd_stats(args):
    import json
    mem, brain, think, feed = _boot()
    print(json.dumps({"memory": mem.stats(), "brain": brain.meta}, indent=2))

def cmd_export(args):
    from . import config, model_file
    mem, brain, think, feed = _boot()
    out = args.out or str(config.BASE / "TenSeiAi.tsei")
    info = model_file.save_model(out, config.BASE)
    print("model file created:", info)
    return 0

def cmd_run(args):
    from pathlib import Path
    model = Path(args.model).expanduser().resolve()
    if not model.exists():
        print("model file not found:", model)
        return 1
    home = os.environ.get("TENSEI_HOME") or str(
        model.parent / (model.name + ".runtime"))
    os.environ["TENSEI_HOME"] = home
    from . import model_file
    info = model_file.install_model(model, home, force=args.force)
    print("model:", model.name, "->", info)
    if getattr(args, "chat", False):
        return cmd_chat(args)
    from .server import main as serve
    serve(args.host, args.port)
    return 0

def cmd_build(args):
    from .build import build_zipapp
    info = build_zipapp(args.out)
    print("single-file build created:", info)
    print("share that ONE file - run it with Python 3.12+ and numpy:")
    print("  python3 TenSeiAi.pyz                        # launcher: terminal or web chat")
    print("  python3 TenSeiAi.pyz m.tsei                 # launcher from a shared model file")
    print("  python3 TenSeiAi.pyz chat --steps           # terminal chat with visible steps")
    print('  python3 TenSeiAi.pyz ask "question"         # one-shot answer')
    print('  python3 TenSeiAi.pyz ask "q" --json         # JSON for apps')
    print('  echo "question" | python3 TenSeiAi.pyz ask -')
    print("  python3 TenSeiAi.pyz serve --port 8765      # OpenAI-compatible API")
    return 0

def cmd_inspect(args):
    from . import model_file
    import json
    print(json.dumps(model_file.describe(args.model), indent=2))
    return 0

def cmd_seed_knowledge(args):
    from .knowledge_pack import seed_knowledge
    mem, brain, think, feed = _boot()
    info = seed_knowledge(mem, log=lambda m: print("[seed]", m),
                          max_articles=args.max, chars_per_article=args.chars,
                          time_budget=args.seconds)
    mem.enforce_size()
    print("knowledge added:", info)
    if args.train:
        meta = brain.train_all(log=lambda m: print(" [train]", m))
        print("brain version:", meta.get("version"), "metrics:", meta.get("metrics"))
    return 0

def cmd_sdk(args):
    import zipfile
    from pathlib import Path
    out = Path(args.out or "tensei_sdk")
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    src = Path(__file__).resolve().parent.parent / "sdk"
    if src.is_dir():
        for f in sorted(src.rglob("*")):
            if f.is_file():
                rel = f.relative_to(src)
                (out / rel).parent.mkdir(parents=True, exist_ok=True)
                (out / rel).write_bytes(f.read_bytes())
                n += 1
    else:
        try:
            with zipfile.ZipFile(Path(sys.argv[0]).resolve()) as z:
                for name in z.namelist():
                    if name.startswith("sdk/") and not name.endswith("/"):
                        rel = name[len("sdk/"):]
                        (out / rel).parent.mkdir(parents=True, exist_ok=True)
                        (out / rel).write_bytes(z.read(name))
                        n += 1
        except Exception as e:
            print("sdk extraction failed:", e)
            return 1
    print("extracted %d SDK files (Python/Java/Kotlin/Rust/C++) to %s/" % (n, out))
    return 0

def main(argv=None):
    p = argparse.ArgumentParser(prog="tensei", description="TenSeiAi - local self-learning AI")
    sub = p.add_subparsers(dest="cmd")

    sp = sub.add_parser("serve", help="run web server + chat UI")
    sp.add_argument("--host", default=None)
    sp.add_argument("--port", default=None, type=int)
    sp.set_defaults(func=lambda a: __import__("tensei.server", fromlist=["main"]).main(a.host, a.port))

    sp = sub.add_parser("ask", help="ask one question (works on Windows/"
                        "Linux/macOS/Android; supports stdin and --json)")
    sp.add_argument("question", nargs="?", default="",
                    help='the question; use "-" to read it from stdin')
    sp.add_argument("--model", default=None,
                    help="run from a shared .tsei model file (unpacks it first)")
    sp.add_argument("--offline", action="store_true",
                    help="no internet: answer only from the local knowledge base")
    sp.add_argument("--json", action="store_true",
                    help="print the result as JSON (for apps/scripts)")
    sp.add_argument("--quiet", action="store_true",
                    help="no progress logs; only the answer on stdout")
    sp.add_argument("-v", "--verbose", action="store_true",
                    help="show thinking progress and execution metrics")
    sp.set_defaults(func=cmd_ask)

    sp = sub.add_parser("launch", help="launcher screen: choose terminal chat or web chat")
    sp.add_argument("--model", default=None,
                    help="run from a shared .tsei model file (unpacks it first)")
    sp.add_argument("--offline", action="store_true",
                    help="no internet: answer only from the local knowledge base")
    sp.add_argument("--steps", action="store_true",
                    help="start with the thinking steps visible in chat")
    sp.add_argument("--host", default=None)
    sp.add_argument("--port", default=None, type=int)
    sp.set_defaults(func=cmd_launch)

    sp = sub.add_parser("chat", help="interactive chat (works with --model FILE)")
    sp.add_argument("--model", default=None,
                    help="run from a shared .tsei model file (unpacks it first)")
    sp.add_argument("--offline", action="store_true",
                    help="no internet: answer only from the local knowledge base")
    sp.add_argument("--steps", action="store_true",
                    help="show the thinking/research steps (default: off)")
    sp.set_defaults(func=cmd_chat)

    sp = sub.add_parser("bridge", help="line-JSON stdin/stdout bridge for host apps")
    sp.set_defaults(func=cmd_bridge)

    sp = sub.add_parser("feed", help="run autofeed headless")
    sp.add_argument("--interval", type=float, default=None)
    sp.add_argument("--topics", default=None, help="comma separated seed topics")
    sp.set_defaults(func=cmd_feed)

    sp = sub.add_parser("train", help="train the brain now")
    sp.set_defaults(func=cmd_train)

    sp = sub.add_parser("stats", help="show memory/brain stats")
    sp.set_defaults(func=cmd_stats)

    sp = sub.add_parser("export", help="pack everything into ONE TenSeiAi.tsei model file")
    sp.add_argument("--out", default=None)
    sp.set_defaults(func=cmd_export)

    sp = sub.add_parser("run", help="run directly from a single model file")
    sp.add_argument("--model", required=True)
    sp.add_argument("--chat", action="store_true",
                    help="start the interactive terminal chat instead of the server")
    sp.add_argument("--offline", action="store_true",
                    help="no internet: answer only from the local knowledge base")
    sp.add_argument("--host", default=None)
    sp.add_argument("--port", default=None, type=int)
    sp.add_argument("--force", action="store_true")
    sp.set_defaults(func=cmd_run)

    sp = sub.add_parser("build", help="build the ONE-file TenSeiAi.pyz (model inside)")
    sp.add_argument("--out", default=None)
    sp.set_defaults(func=cmd_build)

    sp = sub.add_parser("inspect", help="show what is inside a .tsei model file")
    sp.add_argument("model")
    sp.set_defaults(func=cmd_inspect)

    sp = sub.add_parser("seed-knowledge",
                        help="fill the model with a built-in knowledge pack (Wikipedia extracts)")
    sp.add_argument("--max", type=int, default=1200, help="max articles")
    sp.add_argument("--chars", type=int, default=12000, help="max chars stored per article")
    sp.add_argument("--seconds", type=float, default=2400, help="time budget")
    sp.add_argument("--train", action="store_true", help="also retrain the brain afterwards")
    sp.set_defaults(func=cmd_seed_knowledge)

    sp = sub.add_parser("sdk", help="extract client SDKs (Python/Java/Kotlin/Rust/C++)")
    sp.add_argument("--out", default=None)
    sp.set_defaults(func=cmd_sdk)

    args = p.parse_args(argv)
    if not args.cmd:
        p.print_help()
        return 1
    r = args.func(args)
    return r if isinstance(r, int) else 0

if __name__ == "__main__":
    sys.exit(main())
