// TenSeiAi Java client (Java 11+, no dependencies).
// run:  javac TenSeiClient.java && java TenSeiClient "what is gravity"
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class TenSeiClient {
    final String base;
    final HttpClient http = HttpClient.newHttpClient();

    public TenSeiClient(String base) { this.base = base; }

    String get(String path) throws Exception {
        HttpRequest req = HttpRequest.newBuilder(URI.create(base + path)).GET().build();
        return http.send(req, HttpResponse.BodyHandlers.ofString()).body();
    }

    String post(String path, String json) throws Exception {
        HttpRequest req = HttpRequest.newBuilder(URI.create(base + path))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(json)).build();
        return http.send(req, HttpResponse.BodyHandlers.ofString()).body();
    }

    static String jsonStr(String s, String key) {
        Matcher m = Pattern.compile("\"" + key + "\"\\s*:\\s*\"((?:[^\"\\\\]|\\\\.)*)\"").matcher(s);
        return m.find() ? m.group(1) : null;
    }

    public String ask(String q) throws Exception {
        String body = "{\"q\": \"" + q.replace("\\", "\\\\").replace("\"", "\\\"") + "\"}";
        String id = jsonStr(post("/api/ask", body), "id");
        for (int i = 0; i < 600 && id != null; i++) {
            String j = get("/api/job?id=" + id);
            if (j.contains("\"status\": \"done\"") || j.contains("\"status\":\"done\"")) {
                return jsonStr(j, "answer");
            }
            Thread.sleep(500);
        }
        return null;
    }

    public String chat(String userMessage) throws Exception {
        String body = "{\"model\": \"tensei-1\", \"messages\": [{\"role\": \"user\", \"content\": \""
                + userMessage.replace("\\", "\\\\").replace("\"", "\\\"") + "\"}]}";
        return post("/v1/chat/completions", body);
    }

    public static void main(String[] args) throws Exception {
        TenSeiClient ai = new TenSeiClient("http://127.0.0.1:8765");
        String q = args.length > 0 ? String.join(" ", args) : "hello";
        System.out.println(ai.ask(q));
    }
}
