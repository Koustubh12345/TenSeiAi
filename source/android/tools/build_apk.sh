#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
APK_DIR="$(dirname "$HERE")"
REPO="$(dirname "$APK_DIR")"
BUILD="$APK_DIR/build"
ANDROID_JAR="${ANDROID_JAR:-/data/data/com.termux/files/usr/tmp/opencode/android.jar}"

if [ ! -f "$ANDROID_JAR" ]; then
    echo "android.jar not found; set ANDROID_JAR to its path" >&2
    exit 1
fi
if [ ! -f "$REPO/dist/TenSeiAi.pyz" ]; then
    echo "build dist/TenSeiAi.pyz first: python scripts/build_release.py" >&2
    exit 1
fi

echo "[1/7] runtime and assets"
"$HERE/make_runtime.sh"
python3 "$HERE/make_icon.py" "$APK_DIR/res/mipmap-xxhdpi/ic_launcher.png"
mkdir -p "$APK_DIR/assets"
cp "$REPO/dist/TenSeiAi.pyz" "$APK_DIR/assets/TenSeiAi.pyz"
cp "$BUILD/assets/python-stdlib.zip" "$APK_DIR/assets/python-stdlib.zip"

rm -rf "$BUILD/classes" "$BUILD/dex" "$BUILD/apk" "$BUILD/unsigned.apk" "$BUILD/aligned.apk"
mkdir -p "$BUILD/classes" "$BUILD/dex" "$BUILD/apk/lib/arm64-v8a"

echo "[2/7] aapt package"
(
    cd "$APK_DIR"
    aapt package -f -M AndroidManifest.xml -S res -A assets \
        -I "$ANDROID_JAR" -F "$BUILD/unsigned.apk"
)

echo "[3/7] javac"
javac -encoding UTF-8 -source 8 -target 8 -bootclasspath "$ANDROID_JAR" \
    -d "$BUILD/classes" "$APK_DIR"/java/ai/tensei/chat/*.java

echo "[4/7] d8"
d8 --min-api 24 --lib "$ANDROID_JAR" --output "$BUILD/dex" \
    "$BUILD"/classes/ai/tensei/chat/*.class

echo "[5/7] pack dex and native Python"
cp "$BUILD/dex/classes.dex" "$BUILD/apk/classes.dex"
cp "$BUILD/lib/arm64-v8a/"*.so "$BUILD/apk/lib/arm64-v8a/"
(
    cd "$BUILD/apk"
    aapt add "$BUILD/unsigned.apk" classes.dex \
        lib/arm64-v8a/libpythonmain.so \
        lib/arm64-v8a/libpython3.14.so \
        lib/arm64-v8a/libandroid-support.so
)

echo "[6/7] zipalign"
zipalign -f 4 "$BUILD/unsigned.apk" "$BUILD/aligned.apk"

echo "[7/7] sign"
KEYSTORE="${TENSEI_APK_KEYSTORE:-}"
STORE_PASS="${TENSEI_APK_STORE_PASS:-}"
KEY_PASS="${TENSEI_APK_KEY_PASS:-$STORE_PASS}"
ALIAS="${TENSEI_APK_ALIAS:-tensei}"

if [ -z "$KEYSTORE" ] || [ ! -f "$KEYSTORE" ]; then
    cat >&2 <<'EOF'
Set TENSEI_APK_KEYSTORE to an existing keystore, then rerun.
Create one outside this repository, for example:

  keytool -genkeypair -keystore /secure/path/tensei-release.jks \
    -alias tensei -keyalg RSA -keysize 2048 -validity 10000

Export TENSEI_APK_STORE_PASS and TENSEI_APK_KEY_PASS. Never commit the
keystore or passwords.
EOF
    exit 2
fi
if [ -z "$STORE_PASS" ]; then
    echo "TENSEI_APK_STORE_PASS is required" >&2
    exit 2
fi

export TENSEI_APK_STORE_PASS="$STORE_PASS"
export TENSEI_APK_KEY_PASS="$KEY_PASS"
mkdir -p "$APK_DIR/dist"
apksigner sign --ks "$KEYSTORE" --ks-key-alias "$ALIAS" \
    --ks-pass env:TENSEI_APK_STORE_PASS \
    --key-pass env:TENSEI_APK_KEY_PASS \
    --out "$APK_DIR/dist/TenSeiAi.apk" "$BUILD/aligned.apk"
apksigner verify --print-certs "$APK_DIR/dist/TenSeiAi.apk" | head -4
echo "APK ready: $APK_DIR/dist/TenSeiAi.apk ($(du -h "$APK_DIR/dist/TenSeiAi.apk" | cut -f1))"
