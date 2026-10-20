"""TenSeiAi single-file model container (TSM1).

Like a GGUF is a container for llama weights, TSM1 is OUR container for
everything TenSeiAi knows: all trained networks (intent, scorer, embedding
projection, language model) plus its accumulated knowledge database - packed
into ONE file. Load that file anywhere and the whole AI runs.

Layout:
  b"TSM1" | u32 meta_len | meta_json
  u32 n_blobs | (u16 name_len | name | u64 size | bytes)*
"""

import json
import os
import struct
import sys
import time
import zlib
from pathlib import Path

MAGIC = b"TSM1"
MAGIC_COMPRESSED = b"TSMC"

def _pack(meta, blobs, compress=True):
    out = bytearray()
    magic = MAGIC_COMPRESSED if compress else MAGIC
    out += magic
    meta["compressed"] = bool(compress)
    meta_b = json.dumps(meta).encode("utf-8")
    out += struct.pack("<I", len(meta_b)) + meta_b
    out += struct.pack("<I", len(blobs))
    for name, data in blobs.items():
        nb = name.encode("utf-8")
        if compress:
            if name.endswith(".db") or name.endswith(".so") or name.endswith(".npz") or len(data) > 2 * 1024 * 1024:
                try:
                    import lzma
                    blob_bytes = lzma.compress(data, preset=6)
                except Exception:
                    blob_bytes = zlib.compress(data, level=9)
            else:
                blob_bytes = zlib.compress(data, level=9)
        else:
            blob_bytes = data
        out += struct.pack("<H", len(nb)) + nb
        out += struct.pack("<Q", len(blob_bytes)) + blob_bytes
    return bytes(out)

def read_model(path):
    raw = Path(path).read_bytes()
    magic = raw[:4]
    if magic not in (MAGIC, MAGIC_COMPRESSED):
        raise ValueError("not a TenSeiAi model file (bad magic)")
    is_compressed = (magic == MAGIC_COMPRESSED)
    off = 4
    (mlen,) = struct.unpack_from("<I", raw, off)
    off += 4
    meta = json.loads(raw[off:off + mlen].decode("utf-8"))
    off += mlen
    if meta.get("compressed"):
        is_compressed = True
    (n,) = struct.unpack_from("<I", raw, off)
    off += 4
    blobs = {}
    for _ in range(n):
        (nl,) = struct.unpack_from("<H", raw, off)
        off += 2
        name = raw[off:off + nl].decode("utf-8")
        off += nl
        (sz,) = struct.unpack_from("<Q", raw, off)
        off += 8
        blob_data = raw[off:off + sz]
        off += sz
        if is_compressed:
            if blob_data.startswith(b"\xfd7zXZ\x00") or blob_data.startswith(b"]\x00\x00"):
                import lzma
                blob_data = lzma.decompress(blob_data)
            else:
                try:
                    blob_data = zlib.decompress(blob_data)
                except Exception:
                    import lzma
                    blob_data = lzma.decompress(blob_data)
        blobs[name] = blob_data
    return meta, blobs

def save_model(path, home, compress=True):
    """Pack brains/ + knowledge db into one model file."""
    home = Path(home)
    blobs = {}
    stamp = 0.0
    brains = home / "brains"
    if brains.exists():
        for f in sorted(brains.glob("*")):
            if f.is_file() and not f.name.endswith(".tmp"):
                blobs["brains/" + f.name] = f.read_bytes()
                try:
                    stamp = max(stamp, f.stat().st_mtime)
                except Exception:
                    pass
    db = home / "data" / "tensei.db"
    if db.exists():
        try:
            import sqlite3
            c = sqlite3.connect(str(db))
            c.execute("VACUUM")
            c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            c.close()
        except Exception:
            pass
        blobs["data/tensei.db"] = db.read_bytes()
    for p_cand in (home / "lib" / "libpython3.14.so", Path("/data/data/com.termux/files/usr/lib/libpython3.14.so")):
        if p_cand.exists() and p_cand.is_file():
            blobs["lib/libpython3.14.so"] = p_cand.read_bytes()
            break
    for p_cand in (home / "lib" / "libandroid-support.so", Path("/data/data/com.termux/files/usr/lib/libandroid-support.so")):
        if p_cand.exists() and p_cand.is_file():
            blobs["lib/libandroid-support.so"] = p_cand.read_bytes()
            break
    web = home / "web" / "index.html"
    if web.exists() and (os.environ.get("TENSEI_PACK_UI", "1") != "0"):
        blobs["web/index.html"] = web.read_bytes()
        try:
            stamp = max(stamp, web.stat().st_mtime)
        except Exception:
            pass
    ver = "?"
    if "brains/meta.json" in blobs:
        try:
            ver = json.loads(blobs["brains/meta.json"]).get("version", "?")
        except Exception:
            pass
    meta = {
        "format": "TenSeiAi-model",
        "magic": "TSM1",
        "name": "TenSeiAi",
        "brain_version": ver,
        "created": stamp or time.time(),
        "note": "TenSeiAi's own model container (from scratch, not GGUF). "
                "Run it with: python3 -m tensei run --model <file>",
        "blobs": sorted(blobs.keys()),
    }
    data = _pack(meta, blobs, compress=compress)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(path) + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)
    return {"path": str(path), "size_mb": round(len(data) / 1048576, 3),
            "blobs": len(blobs), "brain_version": ver, "compressed": bool(compress)}

def install_model(path, home, force=False):
    """Unpack a model file into a runtime home (used by `run --model` and the
    single-file pyz). Skips work when the same brain version and build are already there."""
    meta, blobs = read_model(path)
    home = Path(home)
    ver_new = meta.get("brain_version")
    created = meta.get("created", 0)
    cur = home / "brains" / "meta.json"
    build_file = home / "brains" / ".build_ts"
    last_build = 0.0
    if build_file.exists():
        try:
            last_build = float(build_file.read_text().strip())
        except Exception:
            pass
    if not force and cur.exists() and ver_new is not None:
        try:
            if (json.loads(cur.read_text()).get("version") == ver_new
                    and (home / "data" / "tensei.db").exists()
                    and abs(last_build - created) < 0.01):
                return {"installed": False, "version": ver_new, "home": str(home)}
        except Exception:
            pass
    for name, data in blobs.items():
        p = home / name
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = str(p) + ".tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, p)
    try:
        build_file.write_text(str(created))
    except Exception:
        pass
    stdlib_p = home / "stdlib" / "python-stdlib.zip"
    if stdlib_p.exists() and not (home / "stdlib" / "lib").exists():
        try:
            import zipfile
            with zipfile.ZipFile(str(stdlib_p), "r") as zlib_in:
                zlib_in.extractall(str(home / "stdlib"))
        except Exception:
            pass
    for suf in ("-wal", "-shm"):
        q = home / "data" / ("tensei.db" + suf)
        if q.exists():
            try:
                q.unlink()
            except Exception:
                pass
    for p_bin in (home / "bin" / "python3", home / "stdlib" / "bin" / "python3"):
        if p_bin.exists():
            try:
                os.chmod(p_bin, 0o755)
            except Exception:
                pass
    stdlib_root = home / "stdlib"
    if stdlib_root.exists():
        sp = str(stdlib_root)
        if sp not in sys.path:
            sys.path.append(sp)
        lib_dir = stdlib_root / "lib"
        if lib_dir.exists():
            sp_lib = str(lib_dir)
            if sp_lib not in sys.path:
                sys.path.append(sp_lib)
            for sub in lib_dir.glob("python*"):
                if sub.is_dir() and str(sub) not in sys.path:
                    sys.path.append(str(sub))
    return {"installed": True, "version": ver_new, "home": str(home),
            "blobs": len(blobs)}

def describe(path):
    meta, blobs = read_model(path)
    sizes = {k: round(len(v) / 1048576, 3) for k, v in blobs.items()}
    file_mb = round(Path(path).stat().st_size / 1048576, 3)
    unpacked_mb = round(sum(len(v) for v in blobs.values()) / 1048576, 3)
    return {"meta": meta, "blob_sizes_mb": sizes,
            "file_size_mb": file_mb, "unpacked_total_mb": unpacked_mb}
