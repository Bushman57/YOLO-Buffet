"""RTSP / file capture with reconnect and FPS throttling."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def is_local_file_video_source(source: str) -> bool:
    """
    True if source refers to an existing file on disk.

    RTSP/HTTP(S)/UDP/TCP URLs are treated as streams (reconnect on read failure).
    """
    s = source.strip()
    if s.lower().startswith(
        ("rtsp://", "rtsps://", "http://", "https://", "udp://", "tcp://", "mms://")
    ):
        return False
    try:
        return Path(s).expanduser().resolve().is_file()
    except OSError:
        return False


@dataclass
class FramePacket:
    bgr: np.ndarray
    t_wall: float
    frame_index: int


class VideoSource:
    """OpenCV-backed source with reconnect and optional FPS cap."""

    def __init__(
        self,
        source: str,
        target_fps: float,
        reconnect_delay_sec: float = 3.0,
    ) -> None:
        self.source = source
        self.target_fps = max(0.1, target_fps)
        self.reconnect_delay_sec = reconnect_delay_sec
        self._cap: cv2.VideoCapture | None = None

    def _open(self) -> cv2.VideoCapture:
        cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video source: {self.source}")
        return cap

    def ensure_open(self) -> None:
        if self._cap is None or not self._cap.isOpened():
            if self._cap is not None:
                self._cap.release()
            self._cap = self._open()

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def frames(self) -> Iterator[FramePacket]:
        self.ensure_open()
        min_interval = 1.0 / self.target_fps
        frame_index = 0
        while True:
            t_loop_start = time.perf_counter()
            if self._cap is None:
                break
            ok, bgr = self._cap.read()
            if not ok or bgr is None:
                if is_local_file_video_source(self.source):
                    # EOF or end of clip — do not reconnect; let outer batch loop advance.
                    logger.info("End of video file: %s", self.source)
                    self.release()
                    break
                logger.warning("Frame read failed; reconnecting in %ss", self.reconnect_delay_sec)
                self.release()
                time.sleep(self.reconnect_delay_sec)
                try:
                    self.ensure_open()
                except Exception as e:
                    logger.error("Reconnect failed: %s", e)
                    time.sleep(self.reconnect_delay_sec)
                continue
            yield FramePacket(
                bgr=bgr,
                t_wall=time.time(),
                frame_index=frame_index,
            )
            frame_index += 1
            elapsed = time.perf_counter() - t_loop_start
            sleep_t = min_interval - elapsed
            if sleep_t > 0:
                time.sleep(sleep_t)


def source_from_settings() -> VideoSource:
    from shared.config import get_settings

    s = get_settings()
    src = s.video_source or ""
    if not src:
        raise ValueError("VIDEO_SOURCE must be set for the worker (RTSP URL or file path).")
    return VideoSource(src, target_fps=s.target_fps)
