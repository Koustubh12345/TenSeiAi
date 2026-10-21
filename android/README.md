# TenSeiAi for Android

This folder is a Chaquopy Android project that runs the TenSeiAi Python engine
on the phone and displays the local chat UI in a WebView.

The full setup, staging, build, signing, and direct-call instructions are in
[`docs/ANDROID.md`](../docs/ANDROID.md).

Quick start:

```bash
# From the repository root
mkdir -p android/app/src/main/assets
cp /path/to/TenSeiAi.tsei android/app/src/main/assets/TenSeiAi.tsei
bash android/sync_engine.sh
```

Then open this folder in Android Studio and press Run. The model is not
included in Git; download it from a release or build it from source.

The Termux path is simpler if you do not need a native app:

```bash
pkg install -y python python-numpy
python TenSeiAi.pyz TenSeiAi.tsei
```
