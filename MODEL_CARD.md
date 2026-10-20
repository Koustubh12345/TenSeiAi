# TenSeiAi model card

## Model details

| Field | Value |
|---|---|
| Name | TenSeiAi |
| Release | 8.0.0 |
| Model type | Hybrid retrieval + deterministic solvers + from-scratch Transformer/MoE language core |
| Language core | 2-block Transformer with top-1 Mixture-of-Experts feed-forward layers |
| Parameters | 19,740,464 |
| Dimensions | dim 512, 2 blocks, 2 heads, 4 experts, FFN 1024, vocab 9000 |
| Training | 7,456 samples, 1,202 seconds, hand-written numpy backpropagation |
| Final training loss | 7.9136 |
| Perplexity | 2734.08 |
| Held-out next-token accuracy | 5.43% |
| Knowledge snapshot | 19,895 Q&A rows, 7,460 passages, 400 topics |
| Container | TSM1/TSMC, LZMA-compressed |
| Runtime | Python 3.12+ and numpy; CPU only |
| License | MIT |

The language core is a real trained model, but it is deliberately small. Most
of the measured answer quality comes from the hybrid system around it:
retrieval, grounding checks, deterministic solvers, and answer composition.
The language core is not presented as a standalone frontier chat model.

## What is in the container

`TenSeiAi.tsei` contains:

- `brains/` trained numpy arrays: intent classifier, relevance scorer,
  embedding projection, LM vocabulary, and Transformer/MoE weights.
- `data/tensei.db` the SQLite knowledge and runtime database snapshot.
- `web/index.html` the local chat UI.

`TenSeiAi.pyz` embeds the same TSM1 model plus the runtime entry point and
packed engine modules. It still uses the host Python interpreter and numpy.

## Intended use

- Local question answering over the shipped knowledge base.
- Offline/private experimentation with a small language system.
- Learning how retrieval, routing, and a tiny Transformer fit together.
- Embedding TenSeiAi in a local web app, desktop tool, or Android app.
- A reproducible reference for building a model container without GGUF.

## Out-of-scope use

- High-stakes medical, legal, financial, or safety-critical decisions.
- Claims that TenSeiAi is a frontier general-purpose LLM.
- Unattended public-internet deployment without authentication and rate limits.
- Using the model as a substitute for professional verification.
- Generating or distributing illegal content.

## Training and data

The language core was trained from scratch on prepared text samples with a
small CPU budget. The knowledge snapshot contains curated Q&A rows, reference
passages, code examples, and general-knowledge material. The repository does
not contain private user conversations; runtime learning stays in the user's
`TENSEI_HOME`.

The training pipeline and seeders are in `source/tools/` and
`source/tensei/`. The benchmark is in `source/bench/bench100.py`.

## Evaluation

The v8 offline benchmark is a fixed 100-question set across five domains:

| Metric | Result |
|---|---:|
| Answer checks passed | 100/100 |
| Warm run time | 5.0 s total (about 0.05 s/question) |

This is a fixed benchmark, not a general capability score. It measures the
hybrid system on questions that overlap its retrieval, solver, and knowledge
coverage. The full method and caveats are in [BENCHMARK.md](BENCHMARK.md).

## Limitations

- Open-ended prose generation is weak compared with a modern large model.
- The model can repeat, truncate, or misunderstand language.
- Retrieval can return outdated or incorrect passages.
- The knowledge snapshot is finite and not a live encyclopedia.
- Live research requires network access and can fail or return poor sources.
- The system has only basic harmful-content screening.
- Code generation is strongest for common, well-specified tasks and is
  syntax-checked only in some paths; review generated code before running it.
- Performance varies by device. numpy is strongly recommended.

## Safety and privacy

- No telemetry, account system, or analytics are included.
- The HTTP server defaults to `127.0.0.1`.
- Web research is optional; `TENSEI_OFFLINE=1` disables it.
- Runtime learning is local SQLite data under `TENSEI_HOME`.
- The model and data are provided as-is; verify important information.
- Report security issues through the process in [SECURITY.md](SECURITY.md).

## License

MIT. See [LICENSE](LICENSE).

