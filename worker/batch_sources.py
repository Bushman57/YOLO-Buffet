"""Resolve VIDEO_SOURCE: single file/URL vs directory of BATCH_101 … BATCH_110 clips."""

from __future__ import annotations

import re
from pathlib import Path

VIDEO_EXTENSIONS = frozenset({".mp4", ".avi", ".mov", ".mkv"})

# BATCH_101 … BATCH_110 (batch 1, clips 01–10)
_BATCH_STEM_RE = re.compile(r"^BATCH_1(0[1-9]|10)$", re.IGNORECASE)


def is_video_directory(path: str | Path) -> bool:
    p = Path(path)
    return p.is_dir()


def batch_label_from_stem(stem: str) -> str:
    """Normalize to BATCH_10n (e.g. batch_101 -> BATCH_101)."""
    m = _BATCH_STEM_RE.match(stem)
    if not m:
        return stem
    suffix = m.group(1)
    return f"BATCH_1{suffix}"


def iter_batch_video_paths(root: str | Path) -> list[tuple[Path, str]]:
    """
    List BATCH_101 … BATCH_110 video files under root, sorted by index.

    Returns list of (absolute_path, batch_label e.g. BATCH_105).

    Raises:
        FileNotFoundError: root does not exist
        ValueError: not a directory, or missing/duplicate batch files
    """
    root_path = Path(root).resolve()
    if not root_path.exists():
        raise FileNotFoundError(f"VIDEO_SOURCE directory does not exist: {root_path}")
    if not root_path.is_dir():
        raise ValueError(f"VIDEO_SOURCE is not a directory: {root_path}")

    expected_indices = [f"{i:02d}" for i in range(1, 11)]  # 01..10
    found: dict[str, Path] = {}

    for p in root_path.iterdir():
        if not p.is_file():
            continue
        if p.suffix.lower() not in VIDEO_EXTENSIONS:
            continue
        stem = p.stem
        m = _BATCH_STEM_RE.match(stem)
        if not m:
            continue
        idx = m.group(1)
        label = batch_label_from_stem(stem)
        if idx in found and found[idx] != p:
            raise ValueError(f"Duplicate batch index {label}: {found[idx]} and {p}")
        found[idx] = p

    missing = [f"BATCH_1{i}" for i in expected_indices if i not in found]
    if len(found) == 0:
        raise ValueError(
            "No BATCH_101 … BATCH_110 video files found in "
            f"{root_path}. Expected files like BATCH_101.mp4 … BATCH_110.mp4 "
            f"(extensions: {', '.join(sorted(VIDEO_EXTENSIONS))})."
        )
    if missing:
        raise ValueError(
            "Batch folder is incomplete. Missing: "
            + ", ".join(missing)
            + f". Found: {sorted(found.keys())} in {root_path}"
        )

    ordered = sorted(found.items(), key=lambda kv: int(kv[0]))
    return [(path.resolve(), batch_label_from_stem(path.stem)) for _, path in ordered]


def resolve_worker_sources(video_source: str) -> list[tuple[str, str | None]]:
    """
    Returns list of (source_string, batch_label_or_none).

    - Directory of BATCH clips: multiple entries with labels.
    - Single file or URL: one entry, label None.
    """
    if not video_source or not video_source.strip():
        return []

    path = Path(video_source)
    if path.exists() and path.is_dir():
        pairs = iter_batch_video_paths(path)
        return [(str(p), label) for p, label in pairs]

    return [(video_source.strip(), None)]
