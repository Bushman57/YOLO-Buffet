"""Optional live preview: draw serving zones + YOLO tracks (Phase 3 calibration / debug)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import cv2
import numpy as np

logger = logging.getLogger(__name__)

_COLOR_ZONE = (255, 255, 0)  # cyan BGR
_COLOR_PERSON = (0, 255, 0)  # green
_COLOR_PLATE = (0, 165, 255)  # orange

_WARNED_IMSHOW = False


@dataclass
class PreviewEventFeed:
    """Rolling list of recent serving-event lines for imshow (time-based expiry)."""

    max_lines: int = 8
    ttl_sec: float = 12.0
    _entries: list[tuple[float, str]] = field(default_factory=list)

    def add(self, wall_time: float, text: str) -> None:
        self._entries.append((wall_time, text))
        self.prune(wall_time)

    def prune(self, wall_time: float) -> None:
        self._entries = [(t, s) for t, s in self._entries if wall_time - t <= self.ttl_sec]
        while len(self._entries) > self.max_lines:
            self._entries.pop(0)

    def lines(self, wall_time: float) -> list[str]:
        self.prune(wall_time)
        return [s for _, s in self._entries]


def draw_overlays(
    frame_bgr: np.ndarray,
    plates: list,
    persons: list,
    zones: list,
    frame_w: int,
    frame_h: int,
    event_lines: list[str] | None = None,
) -> np.ndarray:
    """
    Draw normalized zone polygons and plate/person boxes. Does not mutate the input array.

    zones: list of ZoneSpec (points are normalized 0-1).
    plates/persons: list of TrackedObject with .xyxy, .track_id, .conf
    event_lines: optional recent serving_event summaries (see PreviewEventFeed).
    """
    out = frame_bgr.copy()
    for z in zones:
        pts = z.points
        if not pts or len(pts) < 2:
            continue
        arr = np.array(
            [[int(p[0] * frame_w), int(p[1] * frame_h)] for p in pts],
            dtype=np.int32,
        ).reshape((-1, 1, 2))
        cv2.polylines(out, [arr], isClosed=True, color=_COLOR_ZONE, thickness=2)

    for p in persons:
        _draw_box(out, p.xyxy, _COLOR_PERSON, f"P{p.track_id}", frame_w, frame_h)
    for p in plates:
        _draw_box(out, p.xyxy, _COLOR_PLATE, f"T{p.track_id}", frame_w, frame_h)
    if event_lines:
        _draw_event_lines(out, event_lines)
    return out


def _draw_event_lines(img: np.ndarray, lines: list[str]) -> None:
    """Recent serving_event summaries (top-left, dark background for readability)."""
    y0 = 22
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.45
    thickness = 1
    line_h = 16
    color = (180, 255, 180)
    for i, line in enumerate(lines):
        y = y0 + i * line_h
        if y >= img.shape[0] - 4:
            break
        (tw, th), _ = cv2.getTextSize(line, font, scale, thickness)
        x1, y1 = 2, y - th - 2
        x2, y2 = min(img.shape[1] - 2, 6 + tw), min(img.shape[0] - 2, y + 4)
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 0), -1)
        cv2.putText(img, line, (4, y), font, scale, color, thickness, cv2.LINE_AA)


def _draw_box(
    img: np.ndarray,
    xyxy: tuple[float, float, float, float],
    color: tuple[int, int, int],
    label: str,
    frame_w: int,
    frame_h: int,
) -> None:
    x1, y1, x2, y2 = [int(round(c)) for c in xyxy]
    x1 = max(0, min(x1, frame_w - 1))
    x2 = max(0, min(x2, frame_w - 1))
    y1 = max(0, min(y1, frame_h - 1))
    y2 = max(0, min(y2, frame_h - 1))
    cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
    cv2.putText(
        img,
        label,
        (x1, max(12, y1 - 4)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        color,
        1,
        cv2.LINE_AA,
    )


def imshow_frame(vis: np.ndarray, window_name: str = "Buffet worker preview") -> None:
    """Show one frame in an OpenCV window. Logs once if display is unavailable (headless)."""
    global _WARNED_IMSHOW
    try:
        cv2.imshow(window_name, vis)
        cv2.waitKey(1)
    except cv2.error as e:
        if not _WARNED_IMSHOW:
            logger.warning("OpenCV preview unavailable (headless or no display): %s", e)
            _WARNED_IMSHOW = True
    except Exception as e:
        if not _WARNED_IMSHOW:
            logger.warning("Preview failed: %s", e)
            _WARNED_IMSHOW = True
