"""Build TenSeiAi.pyz - ONE executable file containing the whole AI.

Copy that single file anywhere with Python 3 (Termux, Linux, macOS, Windows)
and run it: it unpacks its embedded model to ~/.tensei_ai and starts serving.
"""

import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

MAIN_SRC = '''\
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _zip_self():
    cands = []
    if sys.argv and sys.argv[0]:
        cands.append(sys.argv[0])
        try:
            cands.append(os.path.abspath(sys.argv[0]))
        except Exception:
            pass
    cands.append(str(HERE))
    try:
        cands.append(str(HERE.resolve()))
    except Exception:
        pass
    main_mod = sys.modules.get("__main__")
    if main_mod and getattr(main_mod, "__file__", None):
        try:
            from pathlib import Path
            mf = Path(main_mod.__file__)
            cands.extend([str(mf), str(mf.parent), str(mf.parent.parent)])
        except Exception:
            pass
    for candidate in cands:
        if not candidate:
            continue
        try:
            import zipfile
            if zipfile.is_zipfile(candidate):
                with zipfile.ZipFile(candidate) as zf:
                    if "TENSEI_MODEL.tsei" in zf.namelist():
                        return candidate
        except Exception:
            continue
    return None


def _boot_home():
    home = Path(os.environ.get("TENSEI_HOME") or (Path.home() / ".tensei_ai"))
    home.mkdir(parents=True, exist_ok=True)
    os.environ["TENSEI_HOME"] = str(home)

    for base_p in (HERE / "stdlib", home / "stdlib"):
        lib_dir = base_p / "lib"
        if lib_dir.exists():
            for p_sub in lib_dir.glob("python*"):
                if p_sub.is_dir() and str(p_sub) not in sys.path:
                    sys.path.append(str(p_sub))
            if str(lib_dir) not in sys.path:
                sys.path.append(str(lib_dir))
        if base_p.exists() and str(base_p) not in sys.path:
            sys.path.append(str(base_p))

    # When the user passes a shared model file (python TenSeiAi.pyz m.tsei),
    # that model wins: do not also unpack the embedded one this launch
    # (avoids double installs and DB churn when switching between the two).
    ext_model = any(a.lower().endswith(".tsei") for a in sys.argv[1:])
    model = HERE / "TENSEI_MODEL.tsei"
    zpath = _zip_self()
    if ext_model:
        model = None
        zpath = None
    if model and model.exists():
        try:
            from tensei import model_file
            info = model_file.install_model(model, home)
            if info.get("installed") and os.environ.get("TENSEI_VERBOSE") == "1":
                print("[TenSeiAi] model unpacked to", home)
        except Exception as e:
            if os.environ.get("TENSEI_VERBOSE") == "1":
                print("[TenSeiAi] model install warning:", e)
    elif zpath:
        try:
            import zipfile
            with zipfile.ZipFile(zpath) as zf:
                if "TENSEI_MODEL.tsei" in zf.namelist():
                    tmp = home / "TENSEI_MODEL.install.tmp"
                    tmp.write_bytes(zf.read("TENSEI_MODEL.tsei"))
                    from tensei import model_file
                    info = model_file.install_model(tmp, home)
                    if info.get("installed") and os.environ.get("TENSEI_VERBOSE") == "1":
                        print("[TenSeiAi] model unpacked to", home)
                    tmp.unlink()
        except Exception as e:
            if os.environ.get("TENSEI_VERBOSE") == "1":
                print("[TenSeiAi] model install warning:", e)
    _extract_native_speed(home, zpath)


def _extract_native_speed(home, zpath=None):
    try:
        import zipfile
        for candidate in (str(HERE), sys.argv[0], zpath):
            if not candidate:
                continue
            try:
                with zipfile.ZipFile(candidate) as z:
                    for name in (
                        "tensei/tensei_rust.dll", "tensei_rust.dll",
                        "tensei/libtensei_rust.so", "libtensei_rust.so",
                        "tensei/libtensei_rust.dylib", "libtensei_rust.dylib",
                        "tensei/cspeed.so", "cspeed.so",
                        "tensei/cspeed.dll", "cspeed.dll"
                    ):
                        try:
                            fname = os.path.basename(name)
                            target = home / fname
                            if not target.exists():
                                target.write_bytes(z.read(name))
                        except KeyError:
                            pass
            except Exception:
                continue
    except Exception:
        pass


def main():
    _boot_home()
    args = sys.argv[1:]
    # `python TenSeiAi.pyz my_model.tsei` opens the launcher (terminal or web chat)
    if args and not args[0].startswith("-") and args[0].lower().endswith(".tsei"):
        args = ["launch", "--model", args[0]] + args[1:]
    if not args:
        try:
            interactive = sys.stdin.isatty()
        except Exception:
            interactive = False
        args = ["launch"] if interactive else ["serve"]
    from tensei.cli import main as cmain
    sys.exit(cmain(args))


if __name__ == "__main__":
    main()
'''


SHELL_BOOTSTRAP = b'''#!/bin/sh
# Launch python runtime on zipapp payload

# 1. Fast path: If python3 or python is already installed, launch immediately
if command -v python3 >/dev/null 2>&1; then
    exec python3 "$0" "$@"
elif command -v python >/dev/null 2>&1; then
    exec python "$0" "$@"
fi

# 2. Python is not installed. Auto-bootstrap environment
echo "================================================================="
echo "[TenSeiAi] Python not found on system."
echo "[TenSeiAi] Auto-installing Python so the AI model can run..."
echo "================================================================="

if [ -d "/data/data/com.termux" ] || [ -n "$TERMUX_VERSION" ]; then
    echo "[TenSeiAi] Termux environment detected."
    echo "[TenSeiAi] Installing python & numpy via pkg..."
    pkg update -y >/dev/null 2>&1 || true
    pkg install -y python numpy || pkg install -y python
    if [ ! -f "$PREFIX/bin/python" ] && [ -f "$PREFIX/bin/python3" ]; then
        ln -sf "$PREFIX/bin/python3" "$PREFIX/bin/python"
    fi
    if [ -n "$PREFIX" ] && [ -d "$PREFIX/bin" ]; then
        cat > "$PREFIX/bin/tensei" <<'EOF_TENSEI'
#!/data/data/com.termux/files/usr/bin/bash
TARGET="$HOME/TenSeiAi.pyz"
if [ ! -f "$TARGET" ]; then
    for cand in "$PWD/TenSeiAi.pyz" "$HOME/Download/TenseiGram/TenSeiAi.pyz" "$HOME/Downloads/TenSeiAi.pyz" /sdcard/Download/TenseiGram/TenSeiAi.pyz /sdcard/Download/TenSeiAi.pyz; do
        if [ -f "$cand" ]; then
            TARGET="$cand"
            break
        fi
    done
fi
if [ -f "$TARGET" ]; then
    exec python3 "$TARGET" "$@"
else
    exec python3 -m tensei "$@"
fi
EOF_TENSEI
        chmod +x "$PREFIX/bin/tensei"
        echo "[TenSeiAi] Global 'tensei' command registered! You can now just type 'tensei'."
    fi
    if command -v python3 >/dev/null 2>&1; then
        echo "[TenSeiAi] Python ready! Starting TenSeiAi..."
        exec python3 "$0" "$@"
    elif command -v python >/dev/null 2>&1; then
        echo "[TenSeiAi] Python ready! Starting TenSeiAi..."
        exec python "$0" "$@"
    fi
elif command -v apt-get >/dev/null 2>&1; then
    echo "[TenSeiAi] Debian/Ubuntu detected. Installing python3..."
    sudo apt-get update -y && sudo apt-get install -y python3 python3-numpy
    exec python3 "$0" "$@"
elif command -v dnf >/dev/null 2>&1; then
    echo "[TenSeiAi] Fedora/RHEL detected. Installing python3..."
    sudo dnf install -y python3 python3-numpy
    exec python3 "$0" "$@"
elif command -v pacman >/dev/null 2>&1; then
    echo "[TenSeiAi] Arch Linux detected. Installing python..."
    sudo pacman -Sy --noconfirm python python-numpy
    exec python3 "$0" "$@"
elif command -v apk >/dev/null 2>&1; then
    echo "[TenSeiAi] Alpine Linux detected. Installing python3..."
    apk add python3 py3-numpy
    exec python3 "$0" "$@"
elif command -v brew >/dev/null 2>&1; then
    echo "[TenSeiAi] macOS Homebrew detected. Installing python..."
    brew install python
    exec python3 "$0" "$@"
fi

echo "[TenSeiAi] Error: Python could not be automatically installed."
echo "[TenSeiAi] Please install Python manually: pkg install python"
exit 1
'''



_CIPHER_KEY = b"TenSeiAi_Neural_Cipher_v4_2026_SecureCore_Android"

_ENCRYPTED_INIT_PY = r"""# Module container loader
import sys, os, zlib, marshal, importlib.abc, pkgutil
from importlib.machinery import ModuleSpec

_K = b"TenSeiAi_Neural_Cipher_v4_2026_SecureCore_Android"

class _TenseiLoader(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def __init__(self, core_bytes):
        raw = bytes(b ^ _K[i % len(_K)] for i, b in enumerate(core_bytes))
        self._m = marshal.loads(zlib.decompress(raw))

    def find_spec(self, fullname, path, target=None):
        if fullname in ("tensei", "sdk") or fullname in self._m:
            is_pkg = (fullname in ("tensei", "sdk"))
            spec = ModuleSpec(fullname, self, is_package=is_pkg)
            if is_pkg:
                spec.submodule_search_locations = [fullname]
            return spec
        return None

    def create_module(self, spec):
        return None

    def exec_module(self, mod):
        fn = mod.__name__
        if fn in ("tensei", "sdk"):
            mod.__file__ = "<%s/__init__>" % fn
            mod.__path__ = [fn]
            mod.__loader__ = self
            return
        enc = self._m.get(fn)
        if not enc:
            raise ImportError("Cannot load encrypted module %s" % fn)
        dec = bytes(b ^ _K[i % len(_K)] for i, b in enumerate(enc))
        src = zlib.decompress(dec).decode("utf-8")
        code = compile(src, "<%s>" % fn, "exec")
        mod.__file__ = "<%s>" % fn
        mod.__loader__ = self
        exec(code, mod.__dict__)

def _init_core():
    core_data = pkgutil.get_data("tensei", "_core.bin")
    if not core_data:
        here = os.path.dirname(os.path.abspath(__file__))
        core_p = os.path.join(here, "_core.bin")
        if os.path.exists(core_p):
            with open(core_p, "rb") as f:
                core_data = f.read()
    if core_data:
        loader = _TenseiLoader(core_data)
        sys.meta_path.insert(0, loader)

_init_core()
"""


def _encrypt_and_stage_code(base_dir, staging_dir):
    """Pack modules into a binary container."""
    import marshal, zlib
    staging_tensei = Path(staging_dir) / "tensei"
    staging_tensei.mkdir(parents=True, exist_ok=True)
    modules = {}

    # 1. Encrypt all tensei/*.py files
    tensei_src = Path(base_dir) / "tensei"
    for py_file in sorted(tensei_src.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        mod_name = py_file.stem
        fullname = "tensei.%s" % mod_name
        src = py_file.read_text(encoding="utf-8")
        comp = zlib.compress(src.encode("utf-8"), level=9)
        enc = bytes(b ^ _CIPHER_KEY[i % len(_CIPHER_KEY)] for i, b in enumerate(comp))
        modules[fullname] = enc

    # 2. Encrypt sdk/*.py if present
    sdk_src = Path(base_dir) / "sdk"
    if sdk_src.is_dir():
        for py_file in sorted(sdk_src.glob("*.py")):
            mod_name = py_file.stem
            fullname = "sdk.%s" % mod_name
            src = py_file.read_text(encoding="utf-8")
            comp = zlib.compress(src.encode("utf-8"), level=9)
            enc = bytes(b ^ _CIPHER_KEY[i % len(_CIPHER_KEY)] for i, b in enumerate(comp))
            modules[fullname] = enc

    # 3. Write encrypted binary core
    raw_dict = marshal.dumps(modules)
    core_bin = bytes(b ^ _CIPHER_KEY[i % len(_CIPHER_KEY)] for i, b in enumerate(zlib.compress(raw_dict, level=9)))
    (staging_tensei / "_core.bin").write_bytes(core_bin)

    # 4. Write protected loader __init__.py
    (staging_tensei / "__init__.py").write_text(_ENCRYPTED_INIT_PY, encoding="utf-8")

    # 5. Copy native acceleration binaries
    for native_name in ("cspeed.so", "cspeed.dll", "tensei_rust.dll", "libtensei_rust.so", "libtensei_rust.dylib", "tensei_rust.so"):
        np = tensei_src / native_name
        if np.exists():
            shutil.copy2(np, staging_tensei / native_name)


def _compile_cspeed(pkg_dir):
    """Compile the C sampling accelerator (cspeed.c) with the system C compiler.
    Returns True if cspeed.so was produced; TenSeiAi works fine without it."""
    import subprocess
    src = Path(pkg_dir) / "cspeed.c"
    so = Path(pkg_dir) / "cspeed.so"
    if not src.exists():
        return False
    for cc in ("cc", "gcc", "clang"):
        try:
            r = subprocess.run([cc, "-O2", "-shared", "-fPIC", str(src),
                                "-o", str(so), "-lm"],
                               capture_output=True, timeout=180)
            if r.returncode == 0 and so.exists():
                return True
        except Exception:
            continue
    return False


def build_zipapp(out=None, home=None):
    from . import config
    from .model_file import save_model

    base = Path(home or config.BASE)
    staging = Path(tempfile.mkdtemp(prefix="tensei_build_"))
    try:
        save_model(staging / "TENSEI_MODEL.tsei", base)
        (staging / "__main__.py").write_text(MAIN_SRC)
        # Encrypt all python code into _core.bin so MT Manager cannot show code
        _encrypt_and_stage_code(base, staging)
        so_file = base / "tensei" / "cspeed.so"
        c_ok = _compile_cspeed(base / "tensei") or so_file.exists()
        if so_file.exists() and not (staging / "tensei" / "cspeed.so").exists():
            shutil.copy2(so_file, staging / "tensei" / "cspeed.so")
        sdk_src = base / "sdk"
        if sdk_src.is_dir():
            shutil.copytree(sdk_src, staging / "sdk",
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        out = Path(out) if out else base / "dist" / "TenSeiAi.pyz"
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp_zip = staging / "_app.zip"
        skip = {"_app.zip", "__pycache__"}
        with zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for root, dirs, files in os.walk(staging):
                dirs[:] = [d for d in dirs if d not in skip]
                for fn in files:
                    if fn in skip:
                        continue
                    p = Path(root) / fn
                    rel = p.relative_to(staging).as_posix()
                    # Store pre-compressed model to prevent inflate overhead
                    if fn.endswith(".tsei"):
                        z.write(p, rel, compress_type=zipfile.ZIP_STORED)
                    else:
                        z.write(p, rel, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        # Copy Rust acceleration binaries if compiled
        for rust_name in ("tensei_rust.dll", "libtensei_rust.so", "libtensei_rust.dylib", "tensei_rust.so"):
            rf = base / "tensei" / rust_name
            if rf.exists():
                shutil.copy2(rf, staging / "tensei" / rust_name)

        payload = tmp_zip.read_bytes()
        with open(out, "wb") as f:
            f.write(SHELL_BOOTSTRAP)
            f.write(payload)
        os.chmod(out, 0o755)
        return {"path": str(out), "size_mb": round(out.stat().st_size / 1048576, 3),
                "c_accelerator": c_ok}
    finally:
        shutil.rmtree(staging, ignore_errors=True)
