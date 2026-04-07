"""VideoSource file vs stream detection and EOF behavior."""

from pathlib import Path

import pytest

from worker.ingest import VideoSource, is_local_file_video_source


def test_is_local_file_video_source(tmp_path: Path):
    f = tmp_path / "clip.mp4"
    f.write_bytes(b"")
    assert is_local_file_video_source(str(f)) is True


def test_is_local_file_video_source_rtsp():
    assert is_local_file_video_source("rtsp://192.168.1.1/stream") is False
    assert is_local_file_video_source("http://example.com/v.mp4") is False


def test_is_local_file_video_source_missing_file(tmp_path: Path):
    assert is_local_file_video_source(str(tmp_path / "nope.mp4")) is False


def test_frames_local_file_exits_on_eof(tmp_path: Path):
    """OpenCV returns ok=False at EOF; iterator must stop (no infinite reconnect)."""
    path = tmp_path / "one_frame.mp4"
    import cv2
    import numpy as np

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(path), fourcc, 5.0, (64, 48))
    assert out.isOpened(), "need OpenCV video writer for test"
    frame = np.zeros((48, 64, 3), dtype=np.uint8)
    out.write(frame)
    out.release()

    src = VideoSource(str(path), target_fps=30.0)
    packets = list(src.frames())
    assert len(packets) >= 1
    src.release()
