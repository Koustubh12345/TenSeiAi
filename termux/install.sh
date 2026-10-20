#!/data/data/com.termux/files/usr/bin/bash
# TenSeiAi one-shot setup for Termux (Android).
#   bash install.sh                 (installs python+numpy, prepares ~/.tensei_ai)
#   bash install.sh /path/TenSeiAi.pyz /path/TenSeiAi.tsei
# creates the `tensei` command so you can just run:  tensei
set -e

PYZ="${1:-}"
TSEI="${2:-}"

echo "[1/4] installing python + numpy ..."
pkg update -y >/dev/null 2>&1 || true
pkg install -y python numpy >/dev/null

DEST="$HOME/tensei"
mkdir -p "$DEST"

if [ -n "$PYZ" ] && [ -f "$PYZ" ]; then
    cp -f "$PYZ" "$DEST/TenSeiAi.pyz"
    echo "[2/4] app  copied -> $DEST/TenSeiAi.pyz"
else
    echo "[2/4] put TenSeiAi.pyz into $DEST/ yourself (e.g. from Downloads),"
    echo "      or re-run: bash install.sh <path-to-TenSeiAi.pyz> <path-to-TenSeiAi.tsei>"
fi

if [ -n "$TSEI" ] && [ -f "$TSEI" ]; then
    cp -f "$TSEI" "$DEST/TenSeiAi.tsei"
    echo "[3/4] model copied -> $DEST/TenSeiAi.tsei"
else
    echo "[3/4] put TenSeiAi.tsei into $DEST/ too (same folder as the .pyz)"
fi

echo "[4/4] creating the tensei command ..."
cat > "$PREFIX/bin/tensei" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
DEST="$HOME/tensei"
cd "$DEST" 2>/dev/null || exit 1
if [ -f TenSeiAi.tsei ]; then
    exec python3 TenSeiAi.pyz TenSeiAi.tsei "$@"
else
    exec python3 TenSeiAi.pyz "$@"
fi
EOF
chmod +x "$PREFIX/bin/tensei"

echo
echo "done.  from now on:"
echo "  tensei                        # launcher: terminal chat or web chat"
echo "  tensei ask \"your question\"    # one-shot answer"
echo
echo "web chat opens on http://127.0.0.1:8765 - in Termux it prints the URL"
echo "(Termux has no browser; open it in your phone browser or use 'termux-open-url')."
