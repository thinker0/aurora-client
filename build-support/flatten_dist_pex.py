#!/usr/bin/env python3
"""Copy dist/**/**/*.pex into dist/*.pex (flat output).

Usage:
  ./pants package ::
  python3 build-support/flatten_dist_pex.py
"""
from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


def main() -> int:
    if not DIST.exists():
        print("dist directory not found")
        return 1

    pex_files = [p for p in DIST.rglob("*.pex") if p.parent != DIST and p.is_file()]
    if not pex_files:
        print("No nested .pex files found under dist/")
        return 0

    for p in pex_files:
        dest = DIST / p.name
        shutil.copy2(p, dest)
        print(f"Copied {p} -> {dest}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
