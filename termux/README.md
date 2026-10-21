# TenSeiAi in Termux

Termux runs the complete engine on Android without root or Android Studio.

```bash
pkg update -y
pkg install -y python python-numpy curl
REPO="Koustubh12345/TenSeiAi"
mkdir -p ~/TenSeiAi && cd ~/TenSeiAi
curl -fL -o TenSeiAi.pyz "https://github.com/$REPO/releases/latest/download/TenSeiAi.pyz"
curl -fL -o TenSeiAi.tsei "https://github.com/$REPO/releases/latest/download/TenSeiAi.tsei"
python TenSeiAi.pyz TenSeiAi.tsei
```

Install the `tensei` shortcut from a local copy:

```bash
bash termux/install.sh ./TenSeiAi.pyz ./TenSeiAi.tsei
tensei ask "Why do earthquakes happen?"
```

For the web UI:

```bash
python TenSeiAi.pyz serve --port 8765
```

Open `http://127.0.0.1:8765` in the phone's browser. Termux has no browser of
its own; install one or use `termux-open-url` from `termux-tools`.

The full guide is in [`docs/ANDROID.md`](../docs/ANDROID.md).
