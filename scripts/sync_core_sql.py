#!/usr/bin/env python3
"""
Sync core SQL from the submodule into the Python package.

- Copies all .sql files from extern/pints-core-sql/sql/** into pints/sql/**
  while preserving subdirectories (core/, seeds/, plugins/).
- Creates convenient top-level shortcuts in pints/sql/ for the common files:
    - pints_core_v1.sql       (from sql/core/)
    - pints_core_seed_v1.sql  (from sql/seeds/)
- Writes the core VERSION into pints/sql/CORE_VERSION (if present).

Usage:
    python scripts/sync_core_sql.py
    # or with custom paths:
    python scripts/sync_core_sql.py --src extern/pints-core-sql/sql --dst pints/sql
"""

from __future__ import annotations
import argparse
import shutil
from pathlib import Path
import sys

DEFAULT_SRC = Path("extern/pints-core-sql/sql")
DEFAULT_DST = Path("pints/sql")
CORE_VERSION_FILE = Path("extern/pints-core-sql/VERSION")

def copy_tree(src: Path, dst: Path) -> list[Path]:
    """Copy all .sql files from src/** to dst/** preserving subdirs. Return list of copied files."""
    copied: list[Path] = []
    for path in src.rglob("*.sql"):
        rel = path.relative_to(src)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied.append(target)
        print(f"[pints-sync] copied: {rel}")
    return copied

def write_core_version(dst: Path, version_file: Path) -> None:
    """Write core VERSION into pints/sql/CORE_VERSION (if VERSION exists in submodule)."""
    if version_file.exists():
        content = version_file.read_text(encoding="utf-8").strip()
        out = dst / "CORE_VERSION"
        out.write_text(content + "\n", encoding="utf-8")
        print(f"[pints-sync] CORE_VERSION = {content}")
    else:
        print("[pints-sync] VERSION file not found in submodule; skipping CORE_VERSION.")

def clean_dst(dst: Path) -> None:
    """Remove existing .sql files in pints/sql (but keep directory structure if desired)."""
    if not dst.exists():
        return
    for path in dst.rglob("*.sql"):
        try:
            path.unlink()
        except Exception as e:
            print(f"[pints-sync] warn: could not remove {path}: {e}")

def main():
    ap = argparse.ArgumentParser(description="Sync SQL files from core submodule into the package.")
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC, help="Source dir (extern/pints-core-sql/sql)")
    ap.add_argument("--dst", type=Path, default=DEFAULT_DST, help="Destination dir (pints/sql)")
    args = ap.parse_args()

    src: Path = args.src
    dst: Path = args.dst

    if not src.exists():
        print(f"[pints-sync] error: source not found: {src}\n"
              f"Did you run:  git submodule update --init --recursive ?", file=sys.stderr)
        sys.exit(1)

    dst.mkdir(parents=True, exist_ok=True)

    # Clean old SQLs to avoid stale files
    clean_dst(dst)

    # Copy tree and create shortcuts
    copied = copy_tree(src, dst)
    if not copied:
        print("[pints-sync] warning: no .sql files found under source.")

    # Write core version (optional)
    write_core_version(dst, CORE_VERSION_FILE)

    print(f"[pints-sync] done. SQL synced to: {dst}")

if __name__ == "__main__":
    main()
