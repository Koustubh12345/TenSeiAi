# TenSeiAi SDKs

TenSeiAi runs as a local HTTP server on `http://127.0.0.1:8765`, so any language
can use the model over plain HTTP and JSON. The standalone application can
extract these clients:

```bash
python TenSeiAi.pyz sdk --out tensei_sdk
```

Start the engine first:

```bash
python TenSeiAi.pyz serve --port 8765
```

## Endpoints

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/api/ask` | `{"q": "...", "wait": true}` | direct answer |
| POST | `/api/ask` | `{"q": "..."}` | `{"id": "..."}` job id |
| GET | `/api/job?id=...` | none | job status and result |
| POST | `/v1/chat/completions` | OpenAI format | OpenAI-compatible response |
| GET | `/api/stats` | none | live brain and memory stats |

## Quick test

```bash
curl -s http://127.0.0.1:8765/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"tensei-1","messages":[{"role":"user","content":"hello"}]}'
```

## Included clients

- `python/tensei_client.py` standard-library Python client
- `java/TenSeiClient.java` Java 11+ client using `java.net.http`
- `kotlin/TenSeiAndroid.kt` Kotlin/Android `HttpURLConnection` helper
- `rust/tensei_client.rs` Rust client using only the standard library
- `cpp/tensei_client.cpp` C++17 POSIX client with no dependencies

These clients are examples, not published packages. Review and adapt them for
your app. The server is intended for local use and has no authentication.
See [`docs/API.md`](../../docs/API.md) and [`SECURITY.md`](../../SECURITY.md).
