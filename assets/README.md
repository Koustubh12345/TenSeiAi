# Release assets

`tensei.db.gz` is the compressed snapshot of the shipped knowledge base.

| Property | Value |
|---|---:|
| Format | gzip-compressed SQLite 3 database |
| Uncompressed size | 107,487,232 bytes (102.51 MiB) |
| Compressed size | 49,733,956 bytes (47.43 MiB) |
| SHA-256 of compressed file | see `SHA256SUMS` |
| Q&A rows | 19,895 |
| Passages | 7,460 |
| Topics | 400 |

## Why the database is compressed

GitHub rejects individual files larger than 100 MB. The uncompressed SQLite
database is slightly larger than that limit, so the repository stores a
deterministic gzip snapshot. `scripts/prepare_assets.py` verifies the checksum
and restores `source/data/tensei.db` before a local run or build.

The gzip file is a source asset, not a user database. Runtime learning is
written to the user's `TENSEI_HOME` (normally `~/.tensei_ai`).

```bash
python scripts/prepare_assets.py
python scripts/prepare_assets.py --force
```
