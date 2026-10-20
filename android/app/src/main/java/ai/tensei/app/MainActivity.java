package ai.tensei.app;

import android.app.Activity;
import android.os.Bundle;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/**
 * TenSeiAi on-device chat app.
 *
 * Copies assets/TenSeiAi.tsei or TenSeiAi.pyz into app storage on first launch,
 * extracts bundled python standard library if needed, boots the TenSeiAi engine
 * through Chaquopy, and shows its chat UI in a WebView served from 127.0.0.1.
 * Everything runs locally and offline on the phone.
 */
public class MainActivity extends Activity {

    private WebView web;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        web = new WebView(this);
        setContentView(web);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        web.setWebViewClient(new WebViewClient());
        web.loadData("<html><body style='background:#121316;color:#e8eaed;font-family:sans-serif;padding:24px;text-align:center;'>"
                + "<h2 style='color:#00e5ff;'>TenSeiAi</h2><p>Starting neural engine & loading local model...</p></body></html>",
                "text/html", "utf-8");

        new Thread(() -> {
            try {
                if (!Python.isStarted()) {
                    Python.start(new AndroidPlatform(this));
                }
                extractAssets();
                String url = Python.getInstance()
                        .getModule("tensei.android")
                        .callAttr("start", getFilesDir().getAbsolutePath())
                        .toString();
                runOnUiThread(() -> web.loadUrl(url));
            } catch (Exception e) {
                final String msg = e.getMessage();
                runOnUiThread(() -> web.loadData(
                        "<html><body style='background:#121316;color:#e8eaed;font-family:sans-serif;padding:24px;'>"
                                + "<h3 style='color:#ff5252;'>TenSeiAi failed to start</h3><pre style='background:#1c1d22;padding:12px;border-radius:8px;overflow-x:auto;'>"
                                + (msg == null ? "Unknown error" : msg)
                                + "</pre></body></html>", "text/html", "utf-8"));
            }
        }).start();
    }

    /** Stage model or zipapp from assets into internal filesDir if not already present. */
    private void extractAssets() {
        File filesDir = getFilesDir();
        String[] modelFiles = {"TenSeiAi.tsei", "TenSeiAi.pyz", "model.tsei", "TENSEI_MODEL.tsei"};
        for (String name : modelFiles) {
            File dest = new File(filesDir, name);
            if (!dest.exists()) {
                copyAsset(name, dest);
            }
        }

        // Also extract python-stdlib.zip from assets if provided
        File stdlibDest = new File(filesDir, "python-stdlib.zip");
        if (!stdlibDest.exists()) {
            copyAsset("python-stdlib.zip", stdlibDest);
        }
        if (stdlibDest.exists()) {
            File stdlibDir = new File(filesDir, "stdlib");
            if (!stdlibDir.exists() || !new File(stdlibDir, "lib").exists()) {
                unzip(stdlibDest, stdlibDir);
            }
        }
    }

    private void copyAsset(String assetName, File destFile) {
        try (InputStream in = getAssets().open(assetName);
             OutputStream out = new FileOutputStream(destFile)) {
            byte[] buf = new byte[1 << 16];
            int n;
            while ((n = in.read(buf)) > 0) {
                out.write(buf, 0, n);
            }
        } catch (Exception ignored) {
            // Asset might not be present; engine will fall back to local files
        }
    }

    private void unzip(File zipFile, File targetDir) {
        try (ZipInputStream zis = new ZipInputStream(new FileInputStream(zipFile))) {
            targetDir.mkdirs();
            ZipEntry ze;
            byte[] buffer = new byte[1 << 16];
            while ((ze = zis.getNextEntry()) != null) {
                File file = new File(targetDir, ze.getName());
                if (ze.isDirectory()) {
                    file.mkdirs();
                } else {
                    file.getParentFile().mkdirs();
                    try (FileOutputStream fos = new FileOutputStream(file)) {
                        int len;
                        while ((len = zis.read(buffer)) > 0) {
                            fos.write(buffer, 0, len);
                        }
                    }
                }
                zis.closeEntry();
            }
        } catch (Exception ignored) {}
    }

    @Override
    public void onBackPressed() {
        if (web != null && web.canGoBack()) {
            web.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
