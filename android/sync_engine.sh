#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/source/tensei"
DST="$(cd "$(dirname "$0")" && pwd)/app/src/main/python/tensei"
ASSETS="$(cd "$(dirname "$0")" && pwd)/app/src/main/assets"
MODEL="${TENSEI_MODEL:-}"

if [ -z "$MODEL" ]; then
    for candidate in \
        "$ROOT/TenSeiAi.tsei" \
        "$ROOT/model/TenSeiAi.tsei" \
        "$ASSETS/TenSeiAi.tsei" \
        "$HOME/Downloads/TenSeiAi.tsei"
    do
        if [ -f "$candidate" ]; then
            MODEL="$candidate"
            break
        fi
    done
fi

rm -rf "$DST"
mkdir -p "$DST" "$ASSETS"
cp -R "$SRC"/. "$DST"/
find "$DST" -name "__pycache__" -type d -prune -exec rm -rf {} +
find "$DST" -name "*.pyc" -delete

printf 'engine -> %s\n' "$DST"
if [ -n "$MODEL" ] && [ -f "$MODEL" ]; then
    cp -f "$MODEL" "$ASSETS/TenSeiAi.tsei"
    printf 'model  -> %s\n' "$ASSETS/TenSeiAi.tsei"
else
    echo "model not found; place TenSeiAi.tsei in android/app/src/main/assets/"
    echo "or run: TENSEI_MODEL=/path/to/TenSeiAi.tsei bash android/sync_engine.sh"
fi
