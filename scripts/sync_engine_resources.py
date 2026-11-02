#!/usr/bin/env python3
"""Keep packaged engine_resources/ identical to the canonical engine/ tree."""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "engine"
TARGET = ROOT / "i_mage_not_ai" / "engine_resources"
SUFFIXES = {".gd", ".cs"}


def iter_engine_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for engine in ("godot", "unity"):
        base = root / engine
        if not base.is_dir():
            raise FileNotFoundError(f"missing engine tree: {base}")
        files.extend(path for path in base.rglob("*") if path.is_file() and path.suffix in SUFFIXES)
    return sorted(files)


def check() -> int:
    mismatches: list[str] = []
    for original in iter_engine_files(SOURCE):
        relative = original.relative_to(SOURCE)
        packaged = TARGET / relative
        if not packaged.is_file():
            mismatches.append(f"missing packaged file: {relative}")
            continue
        if packaged.read_bytes() != original.read_bytes():
            mismatches.append(f"content drift: {relative}")
    if mismatches:
        print("engine/ and i_mage_not_ai/engine_resources/ are out of sync:", file=sys.stderr)
        for line in mismatches:
            print(f"  - {line}", file=sys.stderr)
        print("Run: python scripts/sync_engine_resources.py", file=sys.stderr)
        return 1
    print("engine resources are in sync")
    return 0


def sync() -> int:
    for engine in ("godot", "unity"):
        src = SOURCE / engine
        dst = TARGET / engine
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
    print(f"synced {SOURCE} -> {TARGET}")
    return check()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 when trees differ")
    args = parser.parse_args()
    if args.check:
        return check()
    return sync()


if __name__ == "__main__":
    raise SystemExit(main())
