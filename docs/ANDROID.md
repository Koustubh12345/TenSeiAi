# Android and Termux

TenSeiAi runs on Android in two ways: the quick Termux path and a native
Chaquopy app. The model is local in both cases.

## Option 1: Termux (no root, no Android Studio)

Termux is the fastest way to run the complete engine on a phone.

```bash
pkg update -y
pkg install -y python python-numpy curl
REPO="Koustubh12345/TenSeiAi"
mkdir -p ~/TenSeiAi && cd ~/TenSeiAi
curl -fL -o TenSeiAi.pyz "https://github.com/$REPO/releases/latest/download/TenSeiAi.pyz"
curl -fL -o TenSeiAi.tsei "https://github.com/$REPO/releases/latest/download/TenSeiAi.tsei"
python TenSeiAi.pyz TenSeiAi.tsei
```

For the web chat, start the server and open the URL in the phone browser:

```bash
python TenSeiAi.pyz serve --port 8765
```

`http://127.0.0.1:8765` is on the phone itself. Termux has no built-in browser;
install one or use `termux-open-url` after installing `termux-tools`.

The repository also includes `termux/install.sh` for a local download:

```bash
bash termux/install.sh ./TenSeiAi.pyz ./TenSeiAi.tsei
tensei ask "Why do earthquakes happen?"
```

## Option 2: Native app with Chaquopy

The `android/` directory is a Gradle/Chaquopy project. It runs CPython and
numpy inside the app and displays the same local chat UI in a WebView.

### Prerequisites

- Android Studio with Android SDK 34.
- A released `TenSeiAi.tsei` file.
- Network access for the first Gradle/Chaquopy dependency download.

### Stage the model and engine

```bash
git clone https://github.com/Koustubh12345/TenSeiAi.git
cd TenSeiAi
mkdir -p android/app/src/main/assets
cp /path/to/TenSeiAi.tsei android/app/src/main/assets/TenSeiAi.tsei
bash android/sync_engine.sh
```

`sync_engine.sh` copies `source/tensei/` into the Android project. It accepts a
model path through `TENSEI_MODEL` if the model is stored elsewhere:

```bash
TENSEI_MODEL=/path/to/TenSeiAi.tsei bash android/sync_engine.sh
```

On Windows PowerShell:

```powershell
.\android\sync_engine.ps1 -Model "C:\path\to\TenSeiAi.tsei"
```

### Build and run

Open the `android/` folder in Android Studio and press **Run**. The first build
may take several minutes while Gradle downloads Chaquopy's Python runtime and
numpy.

Command-line builds require a Gradle 8.x installation; this repository does
not ship a Gradle wrapper. From the `android/` folder:

```bash
gradle assembleDebug
```

The APK is written to `android/app/build/outputs/apk/debug/`.

The app is intentionally not published as a prebuilt APK. Build it yourself so
you control the signing key and the model version.

### What happens on first launch

1. `MainActivity` starts Chaquopy and Python.
2. The model is copied from the app assets to app-private storage if needed.
3. `tensei.android.start(home)` boots the engine and serves the UI on
   `127.0.0.1`.
4. The WebView loads the local chat page.

The first launch is slower because the engine unpacks and loads the model.
Later launches reuse the private copy.

## Direct engine calls

For a custom native UI, call the engine without a WebView:

```kotlin
val home = filesDir.absolutePath
val answer = Python.getInstance()
    .getModule("tensei.android")
    .callAttr("ask", home, "What is Big O notation?")
    .toString()
```

To start the local server and get a URL:

```kotlin
val url = Python.getInstance()
    .getModule("tensei.android")
    .callAttr("start", home)
    .toString()
webView.loadUrl(url)
```

## Signing

No keystore is included in this repository. Create your own signing key and
keep it outside the repository. Never commit a `.jks`, `.keystore`, or signing
password.

For a release APK, configure signing in your local Gradle properties or
environment and use a private keystore. See the Android documentation for
`apksigner` and Gradle signing configs.

## Limits

- The model is roughly 80 MB, so the APK and first-launch extraction are large.
- The WebView UI is the same local page as the desktop build.
- Web research requires internet and is optional.
- numpy is strongly recommended for speed.
- The native project is a reference integration, not a Play Store product.
