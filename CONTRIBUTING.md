# Contributing to TenSeiAi

Thanks for helping improve a local, from-scratch AI stack. Contributions are
reviewed for correctness, reproducibility, and respect for the project's
security boundaries.

## Before you start

- Read [README.md](README.md), [MODEL_CARD.md](MODEL_CARD.md), and
  [SECURITY.md](SECURITY.md).
- For a bug, include the version, operating system, Python version, numpy
  version, command used, and the smallest useful reproduction.
- For a feature, explain the user problem and how it fits the local-first
  design. Large features should be discussed in an issue first.

## Development setup

```bash
git clone https://github.com/Koustubh12345/TenSeiAi.git
cd TenSeiAi
python -m pip install -r requirements.txt
python scripts/prepare_assets.py
python -m unittest discover -s source/tests -v
```

The uncompressed database is generated and ignored by Git. Do not commit it.
The release database is `assets/tensei.db.gz`.

## Making changes

- Keep changes focused. Avoid unrelated formatting churn.
- Preserve the existing behavior unless the change is the point of the work.
- Add or update tests for behavior changes.
- Keep the local-first and no-pretrained-model constraints intact.
- Do not introduce telemetry, analytics, hidden network calls, or a required
  hosted API.
- Do not commit generated artifacts, model files, logs, caches, benchmark
  results, or signing material.
- If you add a dependency, explain why it is necessary and update the
  requirements and documentation.

## Code style

- Python 3.12+; prefer the standard library unless a dependency is justified.
- Keep functions focused and names descriptive.
- Comments should explain non-obvious decisions, not restate the code.
- Use UTF-8 for source and documentation.
- Keep the web UI dependency-free unless there is a clear reason.
- Run `python -m compileall -q source` before opening a pull request.

## Tests and benchmark

```bash
python -m unittest discover -s source/tests -v
cd source
TENSEI_OFFLINE=1 TENSEI_NO_LEARN=1 python bench/bench100.py
```

Do not tune the code to a benchmark question. If a fix improves the benchmark,
explain the general behavior it improves.

## Assets and model changes

If you retrain the model or change the shipped knowledge base:

1. Rebuild the snapshot intentionally.
2. Regenerate `assets/tensei.db.gz`.
3. Update `assets/SHA256SUMS` and `assets/README.md`.
4. Update `MODEL_CARD.md` and `CHANGELOG.md`.
5. Run the full build and benchmark.
6. Do not commit the uncompressed database or built `.tsei`/`.pyz`.

The preparation script checks the snapshot hash and row counts. A deliberate
snapshot change must update those values together.

## Android contributions

- No keystore or signing password may be committed.
- Keep the model out of Git; document how to stage it.
- Test both Termux and the Chaquopy project when the change affects mobile.
- Keep Android permissions minimal.

## Pull requests

A good pull request includes:

- what changed and why,
- the commands used to test,
- benchmark impact if relevant,
- any security or privacy implications,
- documentation updates.

By contributing, you agree that your contribution is licensed under the
project's MIT license.
