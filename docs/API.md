# Local HTTP API

TenSeiAi serves a small HTTP API from the same process as the web chat. The
default address is `http://127.0.0.1:8765`. It is intended for local
applications, not as a public multi-user service.

Start it with:

```bash
python TenSeiAi.pyz serve --port 8765
```

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | Local web chat |
| `GET` | `/api/stats` | Memory, brain, and uptime statistics |
| `POST` | `/api/ask` | Ask a question |
| `GET` | `/api/job?id=...` | Poll an asynchronous job |
| `GET` | `/api/feed?since=0` | Recent learning/training events |
| `GET` | `/api/topics` | Current topic queue |
| `POST` | `/api/feedback` | Rate a stored answer |
| `POST` | `/api/autofeed` | Start or stop optional background research |
| `POST` | `/api/train` | Start a background brain training run |
| `GET` | `/v1/models` | OpenAI-style model list |
| `POST` | `/v1/chat/completions` | OpenAI-compatible chat completion |

## Ask

Direct answer:

```bash
curl -s http://127.0.0.1:8765/api/ask \
  -H 'Content-Type: application/json' \
  -d '{"q":"What is a black hole?","wait":true}'
```

The response contains `answer`, `steps`, `sources`, `mode`, `confidence`, and
`took_s`.

Asynchronous job:

```bash
curl -s http://127.0.0.1:8765/api/ask \
  -H 'Content-Type: application/json' \
  -d '{"q":"Explain binary search"}'
```

```json
{"id":"a1b2c3d4e5f6"}
```

Poll it:

```bash
curl -s "http://127.0.0.1:8765/api/job?id=a1b2c3d4e5f6"
```

## OpenAI-compatible chat

```bash
curl -s http://127.0.0.1:8765/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "tensei-1",
    "messages": [
      {"role": "user", "content": "Write a Python function to reverse a string"}
    ]
  }'
```

The response follows the usual `choices[0].message.content` shape. Only the
last user message is used as the question. The model name is informational.

## Stats

```bash
curl -s http://127.0.0.1:8765/api/stats
```

Returns memory counts, brain metadata, autofeed status, and uptime.

## Feedback

```bash
curl -s http://127.0.0.1:8765/api/feedback \
  -H 'Content-Type: application/json' \
  -d '{"qa_id":123,"rating":1}'
```

`rating` is an integer; positive values mark a useful answer, negative values
mark a bad one. The exact interpretation is defined by `Memory.set_feedback`.

## Optional autofeed

Autofeed is off by default. Start and stop it explicitly:

```bash
curl -s http://127.0.0.1:8765/api/autofeed \
  -H 'Content-Type: application/json' \
  -d '{"action":"start"}'

curl -s http://127.0.0.1:8765/api/autofeed \
  -H 'Content-Type: application/json' \
  -d '{"action":"stop"}'
```

When started, it searches the web, stores new passages, and eventually
retrains. Use `TENSEI_OFFLINE=1` to prevent network access.

## Security notes

- No authentication is implemented.
- CORS is permissive for local development.
- The default host is `127.0.0.1`.
- Do not bind to `0.0.0.0` on an untrusted network.
- Put authentication, TLS, request limits, and a reverse proxy in front of it
  if you expose it beyond your machine.

See [SECURITY.md](../SECURITY.md).
