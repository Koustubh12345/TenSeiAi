#!/data/data/com.termux/files/usr/bin/bash
# Stage the embedded CPython runtime for the TenSeiAi APK.
# Layout produced under android/build/:
#   lib/arm64-v8a/libpythonmain.so   (the interpreter; goes to nativeLibraryDir)
#   lib/arm64-v8a/libpython3.14.so, libandroid-support.so
#   assets/python-stdlib.zip         (stdlib + lib-dynload + extra libs/,
#                                     extracted by the app to its files dir)
# The extra shared libs keep their original sonames (libz.so.1 etc.) and are
# resolved at runtime through LD_LIBRARY_PATH, which avoids both the
# "lib*.so" extraction filter and bionic verneed mismatches.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
APK_DIR="$(dirname "$HERE")"
BUILD="$APK_DIR/build"
PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
PYVER="$(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])')"
PYSRC="$PREFIX/lib/python$PYVER"
OUT_LIB="$BUILD/lib/arm64-v8a"
OUT_HOME="$BUILD/pythonhome/lib/python$PYVER"
OUT_EXTRA="$BUILD/extra-libs"

rm -rf "$BUILD/lib" "$BUILD/pythonhome" "$BUILD/extra-libs"
mkdir -p "$OUT_LIB" "$OUT_HOME/lib-dynload" "$OUT_EXTRA" "$BUILD/assets"

echo "[runtime] python $PYVER from $PREFIX"

cp "$PREFIX/bin/python$PYVER" "$OUT_LIB/libpythonmain.so"
cp "$PREFIX/lib/libpython$PYVER.so" "$OUT_LIB/libpython$PYVER.so"
cp "$PREFIX/lib/libandroid-support.so" "$OUT_LIB/libandroid-support.so"

copy_real() {  # real file (follow symlinks) with its original name
  local name="$1" dst="${2:-$1}"
  local p="$PREFIX/lib/$name"
  [ -e "$p" ] || { echo "missing $p"; exit 1; }
  cp -L "$p" "$OUT_EXTRA/$dst"
}
copy_real libbz2.so.1.0
copy_real liblzma.so.5
copy_real libsqlite3.so
copy_real libffi.so
copy_real libexpat.so.1
copy_real libssl.so.3
copy_real libcrypto.so.3
copy_real libz.so.1

for f in "$PYSRC"/lib-dynload/*.so; do
  b="$(basename "$f")"
  case "$b" in
    _test*|_curses*|_dbm.*|_gdbm.*|readline.*|_multiprocessing.*|_zstd.*|xx*) continue ;;
  esac
  cp "$f" "$OUT_HOME/lib-dynload/$b"
done

echo "[runtime] copying stdlib .py tree..."
python3 - "$PYSRC" "$OUT_HOME" <<'PYEOF'
import os, shutil, sys
src, dst = sys.argv[1], sys.argv[2]
skip = {"site-packages", "test", "idlelib", "tkinter", "turtledemo", "lib2to3",
        "ensurepip", "venv", "__pycache__", "lib-dynload"}
n = 0
for root, dirs, files in os.walk(src):
    dirs[:] = [d for d in dirs if d not in skip]
    rel = os.path.relpath(root, src)
    outdir = dst if rel == "." else os.path.join(dst, rel)
    os.makedirs(outdir, exist_ok=True)
    for f in files:
        if f.endswith((".py", ".pth")):
            shutil.copy2(os.path.join(root, f), os.path.join(outdir, f))
            n += 1
print("[runtime] stdlib files:", n)
PYEOF

echo "[runtime] zipping..."
python3 - "$BUILD" "$BUILD/assets/python-stdlib.zip" <<'PYEOF'
import os, sys, zipfile
build, out = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    home = os.path.join(build, "pythonhome")
    for root, dirs, files in os.walk(home):
        for f in files:
            p = os.path.join(root, f)
            z.write(p, os.path.relpath(p, home))
    extra = os.path.join(build, "extra-libs")
    for f in sorted(os.listdir(extra)):
        z.write(os.path.join(extra, f), "libs/" + f)
print("[runtime] zip: stdlib +", len(os.listdir(os.path.join(build, "extra-libs"))), "extra libs")
PYEOF

python3 - "$BUILD" <<'PYEOF'
import json, os, sys
b = sys.argv[1]
def dsize(p):
    return sum(os.path.getsize(os.path.join(r, f))
               for r, _, fs in os.walk(p) for f in fs)
print(json.dumps({
    "native_lib_mb": round(dsize(os.path.join(b, "lib")) / 1048576, 2),
    "stdlib_zip_mb": round(os.path.getsize(os.path.join(b, "assets", "python-stdlib.zip")) / 1048576, 2),
}))
PYEOF
echo "[runtime] done"
