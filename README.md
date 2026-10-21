<div align="center">

# TenSeiAi

### Ultra-Compact, High-Performance AI Engine & Mixture-of-Experts Neural Core

**Engineered in pure Python and NumPy. Zero PyTorch. Zero GGUF. Zero Cloud Dependencies.**

[![Build release artifacts](https://github.com/Koustubh12345/TenSeiAi/actions/workflows/build.yml/badge.svg)](https://github.com/Koustubh12345/TenSeiAi/actions/workflows/build.yml)
[![CodeQL](https://github.com/Koustubh12345/TenSeiAi/actions/workflows/codeql.yml/badge.svg)](https://github.com/Koustubh12345/TenSeiAi/actions/workflows/codeql.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-2ea44f.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776ab.svg)](https://www.python.org/)
[![Model Size](https://img.shields.io/badge/model%20size-19.74M%20params%20%7C%2081%20MB-blue.svg)](#architecture--specifications)
[![Latency](https://img.shields.io/badge/CPU%20latency-~0.05s%20per%20query-emerald.svg)](#benchmark-results)
[![Android APK](https://img.shields.io/badge/Android%20APK-Download-3DDC84.svg?logo=android&logoColor=white)](https://github.com/Koustubh12345/TenSeiAi/releases/latest/download/TenSeiAi.apk)

<br/>

<a href="#overview">Overview</a> •
<a href="#key-capabilities">Key Capabilities</a> •
<a href="#quick-start">Quick Start</a> •
<a href="#screenshots--interface-walkthrough">Screenshots</a> •
<a href="#dual-operational-modes">Offline & Live Modes</a> •
<a href="#architecture--specifications">Architecture</a> •
<a href="#benchmark-results">Benchmark</a> •
<a href="docs/ANDROID.md">Android & Termux</a> •
<a href="docs/API.md">REST API</a>

</div>

---

## Overview

TenSeiAi is an ultra-lightweight, high-speed neural AI system engineered to deliver maximum intelligence per megabyte on consumer hardware. At **19.74 million parameters** bundled into an **~81 MB single-file executable**, it is one of the smallest and fastest neural AI engines available, executing natural language reasoning, mathematics, code synthesis, and question answering with sub-50ms latency on CPU alone.

Unlike conventional large language models that demand tens of gigabytes of VRAM, heavy C++ runtimes, and gigabyte-sized dependencies, TenSeiAi executes natively across Android smartphones (Termux or native APK), Raspberry Pis, laptops, and CPU servers - with **zero external machine learning frameworks** (no PyTorch, no TensorFlow, no GGUF/llama.cpp, and no Hugging Face transformers).

---

## Key Capabilities

* **Minimal Footprint (~81 MB Total):** The entire neural language model, vocabulary, semantic embeddings, curated knowledge base, and local web UI are packed into a single portable executable (`TenSeiAi.pyz`).
* **Ultra-Fast CPU Inference (<0.05s per query):** Vectorized NumPy matrix operations and sparse Mixture-of-Experts routing deliver instant, low-latency execution even on mobile processors.
* **High Accuracy via Hybrid Engineering:** Combines a 4-expert Transformer neural core, dense semantic embeddings, SQLite BM25 retrieval across ~20,000 verified rows, and deterministic solvers for arithmetic, logic, and code synthesis.
* **Air-Gapped Offline Execution:** Strict local-first privacy with zero network calls, zero telemetry, and zero third-party dependencies.
* **Optional Live Research & Self-Learning:** Internet connectivity can be toggled on demand (`/web on`) for real-time web retrieval, documentation lookup, and autonomous background knowledge expansion (`/feed on`).
* **Single-File Zero-Config Distribution:** Runs immediately with standard Python 3.12+ and NumPy. No build tools, C++ compilers, or external runtimes required.

---

## Quick Start

### Android (Direct APK - No Terminal Setup)

For an instant native experience without Termux or Python installation:
1. Download the prebuilt Android package: [**TenSeiAi.apk**](https://github.com/Koustubh12345/TenSeiAi/releases/latest/download/TenSeiAi.apk) (136 MB)
2. Tap install and launch TenSeiAi to chat with the fully self-contained offline neural model directly on your phone.

---

### Android (Termux - Terminal & Web CLI Setup)

Open Termux and run:

```bash
pkg update -y
pkg install -y python python-numpy curl
mkdir -p ~/TenSeiAi && cd ~/TenSeiAi
curl -fL -o TenSeiAi.pyz "https://github.com/Koustubh12345/TenSeiAi/releases/latest/download/TenSeiAi.pyz"

python TenSeiAi.pyz
```

> **Interactive Launcher:** Running `python TenSeiAi.pyz` automatically presents an interactive selection screen allowing you to choose:
> * `[1] Terminal chat` - Direct interactive chat in your shell.
> * `[2] Web chat` - Boots the local server and opens the browser UI on port 8765.

---

### Linux, macOS & Windows Subsystem for Linux (WSL)

```bash
mkdir -p TenSeiAi && cd TenSeiAi
curl -fL -o TenSeiAi.pyz "https://github.com/Koustubh12345/TenSeiAi/releases/latest/download/TenSeiAi.pyz"
curl -fL -o SHA256SUMS "https://github.com/Koustubh12345/TenSeiAi/releases/latest/download/SHA256SUMS"

# Verify cryptographic hash
sha256sum -c SHA256SUMS || shasum -a 256 -c SHA256SUMS

# Install dependency and launch
python3 -m pip install --user numpy
python3 TenSeiAi.pyz
```

---

### Windows (PowerShell)

```powershell
New-Item -ItemType Directory -Force TenSeiAi | Out-Null
Set-Location TenSeiAi
Invoke-WebRequest "https://github.com/Koustubh12345/TenSeiAi/releases/latest/download/TenSeiAi.pyz" -OutFile TenSeiAi.pyz
py -3 -m pip install --user numpy
py TenSeiAi.pyz
```

---

## Screenshots & Interface Walkthrough

### 1. Interactive CLI Launcher & Web Gateway
When launched with `python TenSeiAi.pyz`, the interactive terminal menu lets you choose between instant in-terminal chat or starting the browser console:

![Interactive CLI Launcher](assets/cli_launcher.png)

---

### 2. Local Dark-Mode Web Console & Reasoning Engine
Selecting the web chat boots a local, privacy-focused console at `http://127.0.0.1:8765/` equipped with telemetry metrics, session management, and real-time step-by-step reasoning:

![TenSeiAi Web Console](assets/web_console.png)

---

## Dual Operational Modes

TenSeiAi provides granular control over network connectivity and privacy:

| Feature | Offline Mode (Air-Gapped Default) | Live Research Mode |
| :--- | :--- | :--- |
| **Command** | `python TenSeiAi.pyz chat --offline` | `python TenSeiAi.pyz chat` (or `/web on` in chat) |
| **Network Traffic** | **0 bytes (Strictly air-gapped)** | Outbound HTTPS queries to public knowledge sources |
| **Knowledge Source** | Embedded 19.74M MoE weights + local SQLite snapshot | Local memory augmented with real-time web search |
| **Use Cases** | Private environments, planes, offline edge devices | Current news, live documentation, real-time research |
| **Auto-Learning** | Read-only local memory | Autonomous AutoFeed background learner (`/feed on`) |
| **Inference Latency** | **~0.01s - 0.05s** | ~0.5s - 1.5s (dependent on network speed) |

---

## Architecture & Specifications

```mermaid
flowchart TD
    Prompt["User Prompt (CLI / Web / API)"] --> Router["Intent Classifier & Semantic Dispatcher"]

    Router -->|Mathematics & Logic| MathSolver["Deterministic Solvers (Exact Arithmetic & Logic)"]
    Router -->|Coding & Algorithms| CodeEngine["Code Synthesis Engine"]
    Router -->|Factual Knowledge| HybridMemory["Hybrid Memory: BM25 + Dense Embeddings"]
    Router -->|Live Web Research| WebAgent["Web Research Agent (Optional /web on)"]
    Router -->|Open-Ended Prose| MoECore["19.74M MoE Transformer Core (transmoe.py)"]

    MathSolver --> Composer["Answer Synthesizer & Surface Realizer"]
    CodeEngine --> Composer
    HybridMemory --> Grounding["Semantic Reranking & Verification"]
    Grounding --> Composer
    WebAgent --> Composer
    MoECore --> Composer

    Composer --> FinalAnswer["Final Output: Formatted & Punctuated"]
    FinalAnswer -.->|Verified Facts| LocalMemory["Local SQLite Knowledge Learner"]
```

### Technical Specifications

| Component | Technical Details |
| :--- | :--- |
| **Language Core** | Custom 2-block Transformer with top-1 Mixture-of-Experts (MoE) FFN |
| **Total Parameters** | **19,740,464 parameters** |
| **Model Dimensions** | Hidden dim 512, 2 Attention Heads, 4 Feed-Forward Experts, Vocab 9,000 |
| **Generative Engine (v8.1)** | Strict 3-gram loop blocker, repetition penalties, nucleus top-p (0.88) + top-k (35) sampling, prompt anchor retention, and surface truecasing/punctuation |
| **Knowledge Base** | 19,895 verified Q&A pairs, 7,460 encyclopedic passages, 400 topic clusters |
| **Retrieval Engine** | Hybrid Dense Embedding Projections + SQLite FTS5 / BM25 with strict reranking |
| **Deterministic Solvers** | Multi-step arithmetic, unit conversions, date/calendar math, and logic |
| **Executable Container** | Single-file universal ZipApp (`TenSeiAi.pyz`, ~81 MB) |
| **Model Container** | Native LZMA compressed container (`TenSeiAi.tsei`, ~81 MB) |

---

## Command-Line Usage

```bash
# 1. Interactive menu (Terminal or Web chat)
python TenSeiAi.pyz

# 2. Direct offline terminal chat
python TenSeiAi.pyz chat --offline

# 3. Interactive terminal chat with real-time reasoning steps visible
python TenSeiAi.pyz chat --steps

# 4. Instant one-shot answer
python TenSeiAi.pyz ask "What is the difference between a process and a thread?" --offline

# 5. Structured JSON output for scripts and pipeline integrations
python TenSeiAi.pyz ask "Explain binary search" --json

# 6. Pipe input from standard input (stdin)
echo "Calculate 45 * 12 + 180" | python TenSeiAi.pyz ask -

# 7. Start local server with OpenAI-compatible API
python TenSeiAi.pyz serve --port 8765
```

---

## OpenAI-Compatible REST API

Starting the server exposes an OpenAI-compatible endpoint at `http://127.0.0.1:8765/v1`:

```bash
curl -s http://127.0.0.1:8765/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tensei-1",
    "messages": [
      {"role": "user", "content": "How do transformers work?"}
    ]
  }'
```

### Python Client Integration
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8765/v1",
    api_key="not-needed"
)

response = client.chat.completions.create(
    model="tensei-1",
    messages=[{"role": "user", "content": "Explain binary search in Python."}]
)

print(response.choices[0].message.content)
```

---

## Benchmark Results

Evaluated across a standard 100-question multi-domain offline evaluation set:

| Evaluation Domain | Questions | Passed | Mean Response Latency |
| :--- | :---: | :---: | :---: |
| **Overall Score** | **100** | **100 / 100 (100%)** | **~0.05s** |
| Mathematics & Logic | 20 | 20 / 20 | 0.01s |
| Coding & Algorithms | 20 | 20 / 20 | 0.04s |
| Science & Biology | 20 | 20 / 20 | 0.06s |
| History & Geography | 20 | 20 / 20 | 0.05s |
| General Knowledge & Definitions | 20 | 20 / 20 | 0.05s |

*Run the benchmark locally:*
```bash
python -m unittest discover -s source/tests -v
python source/bench/bench100.py
```

---

## Build from Source

```bash
git clone https://github.com/Koustubh12345/TenSeiAi.git
cd TenSeiAi

# Install dependencies
python -m pip install -r requirements.txt

# Restore and verify the official compressed knowledge asset
python scripts/prepare_assets.py

# Run unit tests
python -m unittest discover -s source/tests -v

# Build the release artifacts (dist/TenSeiAi.pyz and dist/TenSeiAi.tsei)
python scripts/build_release.py
```

---

## Repository Structure

```text
TenSeiAi/
├── assets/                  # Verified knowledge database, checksums, and screenshots
│   ├── cli_launcher.png     # Interactive CLI launcher screenshot
│   ├── web_console.png      # Web chat console screenshot
│   ├── tensei.db.gz         # Official knowledge snapshot (48 MB)
│   └── SHA256SUMS           # Integrity checksums
├── source/
│   ├── tensei/              # Core AI engine, MoE Transformer, memory, solvers, CLI
│   │   ├── transmoe.py      # From-scratch 19.74M MoE language core & generator
│   │   ├── thinker.py       # Intent routing and semantic grounding
│   │   ├── memory.py        # SQLite FTS5 / BM25 and dense embedding search
│   │   ├── brain.py         # Neural network manager and training loop
│   │   ├── server.py        # Local web server & OpenAI-compatible API
│   │   └── cli.py           # Command-line interface and interactive menu
│   ├── brains/              # Pretrained neural weights & vocabulary mappings
│   ├── sdk/                 # Client libraries (Python, Java, Kotlin, Rust, C++)
│   ├── android/             # Android native bridging components
│   ├── tests/               # Unit and regression test suites
│   └── bench/               # 100-question offline benchmark
├── android/                 # Chaquopy Android Studio project
├── termux/                  # Termux installation and launcher scripts
├── docs/                    # Architecture, API, Build, Android, and FAQ docs
├── scripts/                 # Asset preparation and release build scripts
└── .github/                 # CI/CD workflows (Build, CodeQL, Dependabot)
```

---

## Privacy & Security

* **Zero Telemetry:** No user tracking, analytics, phone-home code, or third-party ad networks.
* **Local Binding:** The web UI and API bind strictly to `127.0.0.1` by default.
* **Isolated Offline Execution:** When `TENSEI_OFFLINE=1` is set, network sockets are completely bypassed.
* **Security Advisories:** Report any security concerns through our [Security Policy](SECURITY.md).

---

## License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.
All neural weights, vocabularies, and knowledge snapshot files in this repository are distributed under the same permissive MIT license.
