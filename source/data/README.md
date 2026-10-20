# Runtime data directory

This directory is populated by the build setup:

```bash
python scripts/prepare_assets.py
```

The script verifies `assets/tensei.db.gz` and restores `tensei.db` here.
The database is intentionally not committed in uncompressed form because it
is larger than GitHub's per-file limit.

At runtime, the engine writes learned rows to the active `TENSEI_HOME`
(normally `~/.tensei_ai/data/tensei.db`), not to this source snapshot.
