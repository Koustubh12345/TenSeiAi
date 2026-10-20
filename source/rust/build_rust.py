"""Build helper for TenSeiAi native Rust core.

Compiles source/rust into tensei_rust.dll (Windows), libtensei_rust.so (Linux/Android),
or libtensei_rust.dylib (macOS), then places it into source/tensei for auto-detection.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RUST_DIR = ROOT / "rust"
TENSEI_DIR = ROOT / "tensei"


def build():
    print("[TenSeiAi Rust] Checking for cargo...")
    cargo = shutil.which("cargo")
    if not cargo:
        print("[TenSeiAi Rust] Cargo not found on PATH.")
        print("To compile the native Rust core, install Rust from: https://rustup.rs")
        print("TenSeiAi will continue running using its built-in C/Python engines.")
        return False

    print("[TenSeiAi Rust] Building release cdylib with cargo...")
    cmd = [cargo, "build", "--release"]
    res = subprocess.run(cmd, cwd=str(RUST_DIR))
    if res.returncode != 0:
        print("[TenSeiAi Rust] Cargo build failed.")
        return False

    target_dir = RUST_DIR / "target" / "release"
    exts = [".dll", ".so", ".dylib"]
    built = None
    for f in target_dir.glob("tensei_rust*"):
        if f.suffix in exts:
            built = f
            break
    if not built:
        for f in target_dir.glob("libtensei_rust*"):
            if f.suffix in exts:
                built = f
                break

    if built:
        dest = TENSEI_DIR / built.name
        shutil.copy2(built, dest)
        print(f"[TenSeiAi Rust] Native accelerator ready: {dest}")
        return True
    else:
        print("[TenSeiAi Rust] Build finished but binary not located in target/release.")
        return False


if __name__ == "__main__":
    success = build()
    sys.exit(0 if success else 1)
