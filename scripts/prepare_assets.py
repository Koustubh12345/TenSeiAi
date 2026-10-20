#!/usr/bin/env python3
"""Restore the shipped knowledge database from its compressed release asset."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import os
import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "assets" / "tensei.db.gz"
CHECKSUMS = ROOT / "assets" / "SHA256SUMS"
TARGET = ROOT / "source" / "data" / "tensei.db"

EXPECTED_ASSET_NAME = "tensei.db.gz"
EXPECTED_DB_SHA256 = "5e4afe6ac11769bdace783761cd0b59c4f6bdf390d82590e7b5dcf7ffdc2c26f"
EXPECTED_COUNTS = {"qa": 19895, "docs": 7460, "topics": 400}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def expected_asset_hash() -> str:
    if not CHECKSUMS.exists():
        raise SystemExit(f"missing checksum file: {CHECKSUMS}")
    for line in CHECKSUMS.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[-1] == EXPECTED_ASSET_NAME:
            return parts[0].lower()
    raise SystemExit(f"{CHECKSUMS} does not contain a checksum for {EXPECTED_ASSET_NAME}")


def database_counts(path: Path) -> dict[str, int]:
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    try:
        check = connection.execute("PRAGMA integrity_check").fetchone()
        if not check or check[0] != "ok":
            raise RuntimeError(f"SQLite integrity check failed: {check!r}")
        return {
            "qa": connection.execute("SELECT COUNT(*) FROM qa").fetchone()[0],
            "docs": connection.execute("SELECT COUNT(*) FROM docs").fetchone()[0],
            "topics": connection.execute("SELECT COUNT(*) FROM topics").fetchone()[0],
        }
    finally:
        connection.close()


def validate_database(path: Path) -> dict[str, int]:
    counts = database_counts(path)
    if counts != EXPECTED_COUNTS:
        raise RuntimeError(
            "unexpected database counts: "
            + ", ".join(f"{name}={value}" for name, value in sorted(counts.items()))
            + "; expected "
            + ", ".join(f"{name}={value}" for name, value in sorted(EXPECTED_COUNTS.items()))
        )
    return counts


def prepare(force: bool = False) -> dict[str, int]:
    if not ASSET.exists():
        raise SystemExit(f"missing compressed asset: {ASSET}")

    asset_hash = sha256_file(ASSET)
    wanted_hash = expected_asset_hash()
    if asset_hash != wanted_hash:
        raise SystemExit(
            f"asset checksum mismatch for {ASSET.name}: {asset_hash} != {wanted_hash}"
        )

    if TARGET.exists() and not force:
        target_hash = sha256_file(TARGET)
        if target_hash == EXPECTED_DB_SHA256:
            counts = validate_database(TARGET)
            print(f"database already prepared: {TARGET}")
            print("counts:", " ".join(f"{k}={v}" for k, v in sorted(counts.items())))
            return counts
        raise SystemExit(
            f"{TARGET} already exists but does not match the shipped snapshot.\n"
            "Move it away or rerun with --force to replace it."
        )

    target_dir = TARGET.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    temporary = TARGET.with_suffix(TARGET.suffix + ".tmp")
    try:
        with gzip.open(ASSET, "rb") as source, temporary.open("wb") as destination:
            shutil.copyfileobj(source, destination, length=1024 * 1024)
        restored_hash = sha256_file(temporary)
        if restored_hash != EXPECTED_DB_SHA256:
            raise RuntimeError(
                f"restored database checksum mismatch: {restored_hash} != {EXPECTED_DB_SHA256}"
            )
        counts = validate_database(temporary)
        os.replace(temporary, TARGET)
    finally:
        temporary.unlink(missing_ok=True)
        for suffix in ("-wal", "-shm"):
            Path(str(temporary) + suffix).unlink(missing_ok=True)

    for suffix in ("-wal", "-shm"):
        Path(str(TARGET) + suffix).unlink(missing_ok=True)

    print(f"database restored: {TARGET}")
    print("counts:", " ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace source/data/tensei.db even if it already exists",
    )
    args = parser.parse_args()
    try:
        prepare(force=args.force)
    except (OSError, RuntimeError, sqlite3.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
