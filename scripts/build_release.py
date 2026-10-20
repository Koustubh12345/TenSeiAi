#!/usr/bin/env python3
"""Build TenSeiAi.pyz and TenSeiAi.tsei release artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source"
DEFAULT_OUT = ROOT / "dist"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(command: list[str], env: dict[str, str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=SOURCE, env=env, check=True)


def make_build_home() -> Path:
    home = Path(tempfile.mkdtemp(prefix="tensei_build_home_"))
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo")
    for name in ("tensei", "brains", "data", "web", "sdk"):
        source = SOURCE / name
        if source.exists():
            shutil.copytree(source, home / name, ignore=ignore)
    return home


def verify_pyz(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        required = {"__main__.py", "TENSEI_MODEL.tsei", "tensei/_core.bin"}
        missing = required - names
        if missing:
            raise RuntimeError(f"{path.name} is missing: {', '.join(sorted(missing))}")
        if not archive.read("TENSEI_MODEL.tsei").startswith((b"TSM1", b"TSMC")):
            raise RuntimeError(f"{path.name} does not contain a valid TSM1 model")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--no-prepare", action="store_true")
    parser.add_argument("--prepare-force", action="store_true")
    args = parser.parse_args()

    try:
        import numpy  # noqa: F401
    except ImportError:
        print("error: numpy is required; install it with: python -m pip install -r requirements.txt", file=sys.stderr)
        return 1

    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not args.no_prepare:
        command = [sys.executable, str(ROOT / "scripts" / "prepare_assets.py")]
        if args.prepare_force:
            command.append("--force")
        subprocess.run(command, check=True)

    build_home = make_build_home()
    try:
        env = os.environ.copy()
        env.update(
            {
                "TENSEI_HOME": str(build_home),
                "TENSEI_OFFLINE": "1",
                "TENSEI_NO_LEARN": "1",
                "TENSEI_NO_ANIM": "1",
                "TENSEI_PACK_UI": "1",
                "PYTHONHASHSEED": "0",
            }
        )

        tsei = out_dir / "TenSeiAi.tsei"
        pyz = out_dir / "TenSeiAi.pyz"
        run([sys.executable, "-m", "tensei", "export", "--out", str(tsei)], env)
        run([sys.executable, "-m", "tensei", "build", "--out", str(pyz)], env)

        for path in (pyz, tsei):
            if not path.is_file() or path.stat().st_size < 1_000_000:
                raise RuntimeError(f"build did not produce a valid artifact: {path}")

        verify_pyz(pyz)
        with tsei.open("rb") as handle:
            if handle.read(4) not in (b"TSM1", b"TSMC"):
                raise RuntimeError(f"{tsei.name} has an invalid TSM1 header")

        lines = []
        summary = {}
        for path in (pyz, tsei):
            digest = sha256_file(path)
            lines.append(f"{digest}  {path.name}")
            summary[path.name] = {
                "bytes": path.stat().st_size,
                "sha256": digest,
            }
        (out_dir / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
        summary["output"] = str(out_dir)
        print(json.dumps(summary, indent=2))
        return 0
    finally:
        shutil.rmtree(build_home, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
