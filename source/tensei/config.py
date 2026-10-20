import os
from pathlib import Path

HOME = Path(os.path.expanduser("~"))

def _detect_base():
    env_home = os.environ.get("TENSEI_HOME")
    if env_home:
        return Path(env_home)
    repo = Path(__file__).resolve().parent.parent
    if (repo / "brains").exists() or (repo / "data" / "tensei.db").exists():
        return repo
    cwd = Path.cwd()
    if (cwd / "brains").exists() or (cwd / "data" / "tensei.db").exists():
        return cwd
    return HOME / "TenSeiAi"

BASE = _detect_base()
BRAINS = BASE / "brains"
DATA = BASE / "data"
WEB = BASE / "web"
DB_PATH = DATA / "tensei.db"

def _inject_bundled_stdlib():
    import sys
    # Append at the END so host Python's version-matched stdlib is used first,
    # and bundled stdlib provides missing modules without version syntax conflicts.
    stdlib_dirs = [BASE / "stdlib", Path.home() / ".tensei_ai" / "stdlib"]
    for sdir in stdlib_dirs:
        lib_dir = sdir / "lib"
        if lib_dir.exists():
            for p_sub in lib_dir.glob("python*"):
                if p_sub.is_dir() and str(p_sub) not in sys.path:
                    sys.path.append(str(p_sub))
            if str(lib_dir) not in sys.path:
                sys.path.append(str(lib_dir))
        if sdir.exists() and str(sdir) not in sys.path:
            sys.path.append(str(sdir))

_inject_bundled_stdlib()


HOST = os.environ.get("TENSEI_HOST", "127.0.0.1")
PORT = int(os.environ.get("TENSEI_PORT", "8765"))

EMB_DIM = 192
HASH_DIM = 1 << 14

MAX_BRAIN_MB = 110.0
MAX_DOC_CHARS = 20000
PASSAGE_CHARS = 1600
FETCH_PAGES_PER_QUERY = 4
MAX_MEMORY_PASSAGES = 25000

AF_INTERVAL = 25.0
AF_PAGES_PER_CYCLE = 3
AF_TRAIN_EVERY = 40
AF_MAX_TOPICS = 400

UA = ("Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36 TenSeiAi/1.0")

HTTP_TIMEOUT = 5.0


def ensure_dirs():
    for p in (BRAINS, DATA, WEB):
        p.mkdir(parents=True, exist_ok=True)


def online():
    return os.environ.get("TENSEI_OFFLINE", "0") != "1"


def research_always():
    # "auto" is the fast default: explore the web only when local memory is
    # weak or the question needs live information.  Set TENSEI_RESEARCH=always
    # to force a search for every knowledge question.
    return os.environ.get("TENSEI_RESEARCH", "auto").lower() in (
        "always", "1", "true", "yes", "on")


def brain_meta_path():
    return BRAINS / "meta.json"
