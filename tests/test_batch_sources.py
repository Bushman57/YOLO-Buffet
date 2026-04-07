"""Tests for BATCH_101 … BATCH_110 directory resolution."""

from pathlib import Path

import pytest

from worker.batch_sources import batch_label_from_stem, iter_batch_video_paths, resolve_worker_sources


def test_batch_label_from_stem():
    assert batch_label_from_stem("BATCH_101") == "BATCH_101"
    assert batch_label_from_stem("batch_110") == "BATCH_110"


def test_iter_batch_ordering(tmp_path: Path):
    # Create out of order
    for name in ["BATCH_105.mp4", "BATCH_101.mp4", "BATCH_110.mp4"]:
        (tmp_path / name).write_bytes(b"")
    # Missing 02-04, 06-09 — should raise
    with pytest.raises(ValueError, match="incomplete"):
        iter_batch_video_paths(tmp_path)


def test_iter_batch_full_set_ordered(tmp_path: Path):
    for i in range(1, 11):
        (tmp_path / f"BATCH_1{i:02d}.mp4").write_bytes(b"")
    pairs = iter_batch_video_paths(tmp_path)
    assert len(pairs) == 10
    labels = [lbl for _, lbl in pairs]
    assert labels == [f"BATCH_1{i:02d}" for i in range(1, 11)]


def test_iter_batch_empty_dir(tmp_path: Path):
    with pytest.raises(ValueError, match="No BATCH_101"):
        iter_batch_video_paths(tmp_path)


def test_resolve_single_file():
    pairs = resolve_worker_sources(r"C:\foo\bar.mp4")
    assert pairs == [(r"C:\foo\bar.mp4", None)]


def test_resolve_rtsp():
    u = "rtsp://192.168.1.1:554/stream"
    assert resolve_worker_sources(u) == [(u, None)]
