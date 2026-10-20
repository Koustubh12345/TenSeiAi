# Build and release guide

## Prerequisites

- Python 3.12 or newer.
- numpy 2.x.
- Optional: a C compiler (`cc`, `gcc`, or `clang`) for the `cspeed` sampling
  helper. TenSeiAi works without it.
- About 1 GB free disk space for the source snapshot, restored database, and
  both artifacts.

```bash
python -m pip install -r requirements.txt
```

## 1. Restore the knowledge database

```bash
python scripts/prepare_assets.py
```

The script:

1. Verifies `assets/tensei.db.gz` against `assets/SHA256SUMS`.
2. Decompresses it to `source/data/tensei.db`.
3. Verifies the SQLite integrity check and the expected row counts.
4. Refuses to replace an existing `source/data/tensei.db` that does not match
   the shipped snapshot.

If you intentionally want to replace a modified local source database:

```bash
python scripts/prepare_assets.py --force
```

The uncompressed database is ignored by Git.

## 2. Run the tests

```bash
python -m unittest discover -s source/tests -v
```

The test module creates its own temporary `TENSEI_HOME` and runs offline, so it
does not touch your personal runtime data.

## 3. Build the artifacts

```bash
python scripts/build_release.py
```

The build runs against a temporary copy of `data/`, `brains/`, `web/`, and
`sdk/`, so `source/data/tensei.db` is not mutated.

Outputs:

```text
dist/TenSeiAi.tsei
dist/TenSeiAi.pyz
dist/SHA256SUMS
```

The build script refuses to run without numpy, restores the database when
needed, sets an offline/no-learning build environment, checks both artifact
headers, and writes SHA-256 checksums.

### Build options

```bash
python scripts/build_release.py --out-dir build/release
python scripts/build_release.py --no-prepare
python scripts/build_release.py --prepare-force
```

`--no-prepare` is useful when you already restored and inspected the database.
`--prepare-force` replaces a modified source database with the shipped
snapshot.

## 4. Verify the artifacts

```bash
python dist/TenSeiAi.pyz ask "What is a black hole?"
python dist/TenSeiAi.pyz inspect dist/TenSeiAi.tsei
python dist/TenSeiAi.pyz dist/TenSeiAi.tsei
python dist/TenSeiAi.pyz serve --port 8765
```

The `.tsei` file is a model container, not a standalone executable. Run it with
the `.pyz` runtime, or pass it to an application through
`tensei.model_file.install_model`.

## GitHub Actions

The workflow at `.github/workflows/build.yml` runs on:

- manual dispatch,
- pushes to `main`,
- version tags matching `v*`,
- pull requests targeting `main`.

It performs a clean checkout, installs the pinned numpy version, restores the
asset, runs tests, builds both artifacts, verifies their headers, and uploads
the release artifact. A tag build also creates a GitHub Release and attaches
the artifacts and checksums.

Recommended first release:

```bash
git tag v8.0.0
git push origin v8.0.0
```

No signing key or model download is needed. The workflow uses the repository's
`GITHUB_TOKEN` with job-scoped permissions.

## Repository size strategy

GitHub rejects individual files larger than 100 MB. The uncompressed knowledge
database is 102.51 MiB (107,487,232 bytes). The repository therefore stores a
47.43 MiB gzip snapshot:

```text
assets/tensei.db.gz   49,733,956 bytes
```

The asset is under the limit and does not require Git LFS. The uncompressed
database is recreated locally and by CI. The `assets/SHA256SUMS` file is the
source of truth for the compressed asset.

Do not commit:

- `dist/`
- `*.pyz` or `*.tsei`
- `source/data/tensei.db`
- runtime databases under `~/.tensei_ai`
- Android keystores
- logs, benchmark result dumps, or caches

## Android builds

See [ANDROID.md](ANDROID.md). Android signing keys must be supplied through
your own secure environment and must never be committed.

## Troubleshooting

### `ModuleNotFoundError: numpy`

```bash
python -m pip install -r requirements.txt
```

Use the same Python interpreter that runs `TenSeiAi.pyz`.

### Database checksum mismatch

Download the repository again or verify `assets/SHA256SUMS`. A partial Git
checkout can leave a truncated asset.

### Existing database mismatch

Your source tree has a modified database. Move it away, or deliberately replace
it:

```bash
python scripts/prepare_assets.py --force
```

### The build is slow

The `.tsei` pack compresses the database and brains with LZMA. The first build
can take several minutes on a laptop. Later builds reuse the restored database.
