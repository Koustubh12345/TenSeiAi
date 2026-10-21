# Frequently asked questions

## Is TenSeiAi a wrapper around Llama or GGUF?

No. It does not load a Llama checkpoint, a GGUF file, Ollama, llama.cpp, or a
hosted model. The language core is trained from scratch with numpy, and the
model is stored in TenSeiAi's own TSM1/TSMC container. The `.tsei` extension is
not a renamed GGUF file.

## Do I need a GPU?

No. It runs on a CPU. numpy is strongly recommended. The small C sampling
helper is optional.

## Do I need to install anything?

You need Python 3.12+ and numpy. The release `.pyz` does not bundle CPython or
numpy. On Termux, `pkg install -y python python-numpy` is enough.

## What is the difference between `TenSeiAi.pyz` and `TenSeiAi.tsei`?

`TenSeiAi.pyz` is the standalone application: runtime, web UI, CLI, and an
embedded model. `TenSeiAi.tsei` is the shareable model container. It is not a
standalone executable; run it with the `.pyz` or load it in an app.

```bash
python TenSeiAi.pyz TenSeiAi.tsei
```

## Is it fully offline?

The engine is local and the default HTTP server binds to localhost. Web
research is optional. For a fully offline session:

```bash
TENSEI_OFFLINE=1 python TenSeiAi.pyz
```

On Windows PowerShell:

```powershell
$env:TENSEI_OFFLINE = "1"
py TenSeiAi.pyz
```

## Does it send telemetry?

No telemetry or analytics are included. When web research is enabled, search
queries and fetched URLs go to external services. Disable it with
`TENSEI_OFFLINE=1`.

## Why is the model only about 19.7M parameters?

A small model can run on a CPU and fit in a portable file. TenSeiAi compensates
with retrieval, grounding, deterministic solvers, and a curated knowledge
base. It is not a frontier language model, and the model card says so plainly.

## How accurate is it?

On the fixed v8 100-question benchmark, the hybrid system passed 100/100. That
is a narrow fixed set, not a general capability score. Read
[BENCHMARK.md](../BENCHMARK.md) before quoting it.

## Does it learn from my chats?

Runtime learning is local SQLite data under `TENSEI_HOME` (normally
`~/.tensei_ai`). It is not uploaded. You can delete that directory to reset the
runtime. Builds and benchmarks use a temporary or source database.

## Can I use it commercially?

The code and weights are MIT licensed. See [LICENSE](../LICENSE). You are
responsible for the content you generate and for third-party rights in any
material you add.

## How do I update?

Download the newest release `TenSeiAi.pyz` and optional `TenSeiAi.tsei`, or
rebuild from source. Runtime data remains in `TENSEI_HOME` unless you remove
it.

## Why is the repository's database compressed?

The uncompressed SQLite snapshot is 102.5 MiB, above GitHub's 100 MB per-file
limit. The repository stores a 47.4 MiB gzip asset and restores it with
`scripts/prepare_assets.py`. No Git LFS is required.

## Can I use it from my own app?

Yes. Use the local HTTP API, or on Android use `tensei.android.start` /
`tensei.android.ask` with Chaquopy. See [API.md](API.md) and
[ANDROID.md](ANDROID.md).

## Why does my first run take longer?

The first run unpacks and loads the model into `~/.tensei_ai`. Later runs reuse
the installed model. Use a persistent disk; temporary home directories cause
the unpack to happen repeatedly.

## How do I reset it?

Remove the runtime directory:

```bash
rm -rf ~/.tensei_ai
```

On Windows:

```powershell
Remove-Item -Recurse -Force "$HOME\.tensei_ai"
```

This deletes learned rows and the installed model copy. It does not modify the
release file or the source snapshot.
