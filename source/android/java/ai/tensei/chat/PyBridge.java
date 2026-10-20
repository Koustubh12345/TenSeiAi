package ai.tensei.chat;

import android.content.Context;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/**
 * Runs the TenSeiAi model file (assets/TenSeiAi.pyz) with the embedded
 * CPython runtime and talks to it over a line-JSON bridge:
 *   send  {"q": "..."}
 *   get   {"answer": "...", "mode": "...", "confidence": 0.9, "took_s": 1.2}
 */
public class PyBridge {

    public interface Listener {
        void onStatus(String message);
        void onReady(String version);
        void onAnswer(String answer, String mode, double confidence);
        void onError(String message);
    }

    private final Context ctx;
    private final Object writeLock = new Object();
    private volatile Listener listener;
    private volatile Process proc;
    private volatile BufferedWriter out;
    private volatile boolean ready = false;
    private volatile boolean stopped = false;

    public PyBridge(Context ctx) {
        this.ctx = ctx.getApplicationContext();
    }

    public boolean isReady() {
        return ready;
    }

    public void start(Listener l) {
        this.listener = l;
        Thread t = new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    startBlocking();
                } catch (Throwable e) {
                    reportError("Model start failed: " + e);
                }
            }
        }, "tensei-start");
        t.setDaemon(true);
        t.start();
    }

    private void startBlocking() throws Exception {
        File files = ctx.getFilesDir();
        status("Preparing model file (first run only)...");
        File modelDir = new File(files, "model");
        modelDir.mkdirs();
        File pyz = new File(modelDir, "TenSeiAi.pyz");
        copyAsset("TenSeiAi.pyz", pyz);

        File home = new File(files, "pythonhome");
        File libs = new File(files, "libs");
        File marker = new File(files, "runtime.ok");
        if (!marker.exists() || !new File(home, "lib").isDirectory()) {
            status("Unpacking Python runtime (first run only)...");
            extractZip("python-stdlib.zip", home, libs);
            try {
                marker.createNewFile();
            } catch (IOException ignored) {
            }
        }

        File appHome = new File(files, "home");
        appHome.mkdirs();
        File tmp = new File(files, "tmp");
        tmp.mkdirs();

        String nativeDir = ctx.getApplicationInfo().nativeLibraryDir;
        File interp = new File(nativeDir, "libpythonmain.so");
        if (!interp.exists()) {
            throw new IOException("interpreter missing in " + nativeDir);
        }

        status("Starting TenSeiAi brain...");
        ProcessBuilder pb = new ProcessBuilder(
                interp.getAbsolutePath(), pyz.getAbsolutePath(), "bridge");
        pb.directory(appHome);
        Map<String, String> env = pb.environment();
        env.put("HOME", appHome.getAbsolutePath());
        env.put("PYTHONHOME", home.getAbsolutePath());
        env.put("LD_LIBRARY_PATH", libs.getAbsolutePath() + ":" + nativeDir);
        env.put("PYTHONUNBUFFERED", "1");
        env.put("PYTHONDONTWRITEBYTECODE", "1");
        env.put("TMPDIR", tmp.getAbsolutePath());
        proc = pb.start();

        out = new BufferedWriter(new OutputStreamWriter(proc.getOutputStream(), "UTF-8"));

        final BufferedReader reader = new BufferedReader(
                new InputStreamReader(proc.getInputStream(), "UTF-8"));
        Thread rt = new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    String line;
                    while ((line = reader.readLine()) != null) {
                        handleLine(line);
                    }
                } catch (Throwable ignored) {
                }
                if (!stopped) {
                    reportError("The model process stopped unexpectedly.");
                }
            }
        }, "tensei-reader");
        rt.setDaemon(true);
        rt.start();

        final InputStream es = proc.getErrorStream();
        Thread et = new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    BufferedReader er = new BufferedReader(
                            new InputStreamReader(es, "UTF-8"));
                    BufferedWriter log = new BufferedWriter(new OutputStreamWriter(
                            new FileOutputStream(new File(ctx.getFilesDir(),
                                    "tensei_app.log"), true), "UTF-8"));
                    String line;
                    while ((line = er.readLine()) != null) {
                        log.write(line);
                        log.write("\n");
                        log.flush();
                    }
                    log.close();
                } catch (Throwable ignored) {
                }
            }
        }, "tensei-log");
        et.setDaemon(true);
        et.start();
    }

    private void handleLine(String line) {
        if (line == null || line.length() == 0) {
            return;
        }
        if (line.contains("\"ready\"")) {
            ready = true;
            final String ver = String.valueOf((long) extractNumber(line, "version"));
            post(new Runnable() {
                @Override
                public void run() {
                    Listener l = listener;
                    if (l != null) {
                        l.onReady(ver);
                    }
                }
            });
            return;
        }
        String err = extractString(line, "error");
        if (err != null) {
            reportError(err);
            return;
        }
        final String answer = extractString(line, "answer");
        if (answer != null) {
            final String mode = extractString(line, "mode");
            final double conf = extractNumber(line, "confidence");
            post(new Runnable() {
                @Override
                public void run() {
                    Listener l = listener;
                    if (l != null) {
                        l.onAnswer(answer, mode == null ? "" : mode, conf);
                    }
                }
            });
        }
    }

    public void ask(final String question) {
        Thread t = new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    synchronized (writeLock) {
                        if (out == null) {
                            throw new IOException("bridge not running");
                        }
                        out.write("{\"q\": \"" + jsonEscape(question) + "\"}\n");
                        out.flush();
                    }
                } catch (Throwable e) {
                    reportError("Send failed: " + e);
                }
            }
        }, "tensei-ask");
        t.setDaemon(true);
        t.start();
    }

    public void stop() {
        stopped = true;
        try {
            if (out != null) {
                out.close();
            }
        } catch (Throwable ignored) {
        }
        try {
            if (proc != null) {
                proc.destroy();
            }
        } catch (Throwable ignored) {
        }
    }

    private void status(final String s) {
        post(new Runnable() {
            @Override
            public void run() {
                Listener l = listener;
                if (l != null) {
                    l.onStatus(s);
                }
            }
        });
    }

    private void reportError(final String s) {
        post(new Runnable() {
            @Override
            public void run() {
                Listener l = listener;
                if (l != null) {
                    l.onError(s);
                }
            }
        });
    }

    private void post(Runnable r) {
        android.os.Handler h = new android.os.Handler(
                android.os.Looper.getMainLooper());
        h.post(r);
    }

    private void copyAsset(String name, File dst) throws IOException {
        android.content.res.AssetManager am = ctx.getAssets();
        InputStream is = am.open(name);
        try {
            long assetSize = -1;
            try {
                android.content.res.AssetFileDescriptor fd = am.openFd(name);
                assetSize = fd.getLength();
                fd.close();
            } catch (IOException ignored) {
            }
            if (dst.exists() && assetSize > 0 && dst.length() == assetSize) {
                return;
            }
            File tmp = new File(dst.getAbsolutePath() + ".part");
            FileOutputStream fos = new FileOutputStream(tmp);
            byte[] buf = new byte[65536];
            int n;
            while ((n = is.read(buf)) > 0) {
                fos.write(buf, 0, n);
            }
            fos.close();
            if (dst.exists()) {
                dst.delete();
            }
            if (!tmp.renameTo(dst)) {
                throw new IOException("cannot place " + dst);
            }
        } finally {
            is.close();
        }
    }

    private void extractZip(String asset, File home, File libs) throws IOException {
        ZipInputStream zis = new ZipInputStream(ctx.getAssets().open(asset));
        try {
            byte[] buf = new byte[65536];
            ZipEntry e;
            while ((e = zis.getNextEntry()) != null) {
                String name = e.getName();
                if (e.isDirectory()) {
                    continue;
                }
                File target;
                if (name.startsWith("libs/")) {
                    target = new File(libs, name.substring("libs/".length()));
                } else if (name.startsWith("lib/")) {
                    target = new File(home, name);
                } else {
                    target = new File(home, name);
                }
                File parent = target.getParentFile();
                if (parent != null) {
                    parent.mkdirs();
                }
                FileOutputStream fos = new FileOutputStream(target);
                int n;
                while ((n = zis.read(buf)) > 0) {
                    fos.write(buf, 0, n);
                }
                fos.close();
            }
        } finally {
            zis.close();
        }
    }

    static String extractString(String json, String key) {
        int i = json.indexOf("\"" + key + "\"");
        if (i < 0) {
            return null;
        }
        int c = json.indexOf(':', i + key.length() + 2);
        if (c < 0) {
            return null;
        }
        int q = c + 1;
        while (q < json.length() && Character.isWhitespace(json.charAt(q))) {
            q++;
        }
        if (q >= json.length() || json.charAt(q) != '"') {
            return null;
        }
        StringBuilder sb = new StringBuilder();
        boolean esc = false;
        for (int j = q + 1; j < json.length(); j++) {
            char ch = json.charAt(j);
            if (esc) {
                switch (ch) {
                    case 'n': sb.append('\n'); break;
                    case 't': sb.append('\t'); break;
                    case 'r': sb.append('\r'); break;
                    case 'b': sb.append('\b'); break;
                    case 'f': sb.append('\f'); break;
                    case 'u':
                        if (j + 4 < json.length()) {
                            try {
                                sb.append((char) Integer.parseInt(
                                        json.substring(j + 1, j + 5), 16));
                            } catch (NumberFormatException ignored) {
                            }
                            j += 4;
                        }
                        break;
                    default: sb.append(ch);
                }
                esc = false;
            } else if (ch == '\\') {
                esc = true;
            } else if (ch == '"') {
                break;
            } else {
                sb.append(ch);
            }
        }
        return sb.toString();
    }

    static double extractNumber(String json, String key) {
        int i = json.indexOf("\"" + key + "\"");
        if (i < 0) {
            return 0.0;
        }
        int c = json.indexOf(':', i + key.length() + 2);
        if (c < 0) {
            return 0.0;
        }
        int j = c + 1;
        while (j < json.length() && Character.isWhitespace(json.charAt(j))) {
            j++;
        }
        int k = j;
        while (k < json.length()) {
            char ch = json.charAt(k);
            if ((ch >= '0' && ch <= '9') || ch == '.' || ch == '-' || ch == '+'
                    || ch == 'e' || ch == 'E') {
                k++;
            } else {
                break;
            }
        }
        try {
            return Double.parseDouble(json.substring(j, k));
        } catch (Exception e) {
            return 0.0;
        }
    }

    static String jsonEscape(String s) {
        StringBuilder sb = new StringBuilder(s.length() + 16);
        for (int i = 0; i < s.length(); i++) {
            char ch = s.charAt(i);
            switch (ch) {
                case '"': sb.append("\\\""); break;
                case '\\': sb.append("\\\\"); break;
                case '\n': sb.append("\\n"); break;
                case '\r': sb.append("\\r"); break;
                case '\t': sb.append("\\t"); break;
                default:
                    if (ch < 0x20) {
                        sb.append(String.format("\\u%04x", (int) ch));
                    } else {
                        sb.append(ch);
                    }
            }
        }
        return sb.toString();
    }
}
