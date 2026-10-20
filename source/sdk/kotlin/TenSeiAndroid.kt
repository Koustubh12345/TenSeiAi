// TenSeiAi Kotlin client for Android (no dependencies besides the platform).
// Usage:
//   TenSei("http://127.0.0.1:8765").ask("hello") { answer -> runOnUiThread { textView.text = answer } }
package ai.tensei.sdk

import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL
import kotlin.concurrent.thread

class TenSei(private val base: String = "http://127.0.0.1:8765") {

    private fun request(path: String, method: String, body: String? = null): String {
        val conn = URL(base + path).openConnection() as HttpURLConnection
        conn.requestMethod = method
        conn.connectTimeout = 5000
        conn.readTimeout = 300000
        if (body != null) {
            conn.doOutput = true
            conn.setRequestProperty("Content-Type", "application/json")
            conn.outputStream.use { it.write(body.toByteArray()) }
        }
        val stream = if (conn.responseCode < 400) conn.inputStream else conn.errorStream
        return BufferedReader(InputStreamReader(stream)).readText()
    }

    fun ask(question: String, onAnswer: (String) -> Unit) = thread {
        try {
            val jobId = JSONObject(request("/api/ask", "POST",
                JSONObject(mapOf("q" to question)).toString())).getString("id")
            var i = 0
            while (i++ < 600) {
                val job = JSONObject(request("/api/job?id=$jobId", "GET"))
                if (job.optString("status") == "done") {
                    onAnswer(job.getJSONObject("result").optString("answer"))
                    return@thread
                }
                Thread.sleep(500)
            }
            onAnswer("(timeout)")
        } catch (e: Exception) {
            onAnswer("(error: ${e.message})")
        }
    }

    fun chat(message: String): String {
        val payload = JSONObject()
            .put("model", "tensei-1")
            .put("messages", org.json.JSONArray().put(
                JSONObject().put("role", "user").put("content", message)))
        return request("/v1/chat/completions", "POST", payload.toString())
    }

    fun stats(): String = request("/api/stats", "GET")
}
