#!/usr/bin/env python3
"""Print which BATCH_101 … BATCH_110 files are present or missing in a directory."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from worker.batch_sources import VIDEO_EXTENSIONS, iter_batch_video_paths


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "directory",
        nargs="?",
        default="video_samples",
        type=Path,
        help="Folder to scan (default: video_samples)",
    )
    args = p.parse_args()
    root = args.directory.resolve()

    if not root.exists():
        print(f"ERROR: path does not exist: {root}", file=sys.stderr)
        return 2
    if not root.is_dir():
        print(f"ERROR: not a directory: {root}", file=sys.stderr)
        return 2

    print(f"Scanning: {root}")
    print(f"Expected stems: BATCH_101 - BATCH_110; extensions: {', '.join(sorted(VIDEO_EXTENSIONS))}")
    print()

    try:
        pairs = iter_batch_video_paths(root)
    except ValueError as e:
        print(f"INVALID: {e}")
        return 1

    for path, label in pairs:
        print(f"  OK  {label}  ->  {path.name}")
    print()
    print("All 10 batch clips found. Set VIDEO_SOURCE to this directory.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
