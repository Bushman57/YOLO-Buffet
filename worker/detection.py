"""YOLOv8 + ByteTrack (via Ultralytics track API)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
from ultralytics import YOLO

from worker.events import ZoneSpec

logger = logging.getLogger(__name__)


@dataclass
class TrackedObject:
    track_id: int
    cls_id: int
    xyxy: tuple[float, float, float, float]
    conf: float


def zone_union_roi_pixels(
    zones: list[ZoneSpec],
    frame_w: int,
    frame_h: int,
    padding_frac: float,
) -> tuple[int, int, int, int] | None:
    """
    Axis-aligned bounding box of all zone polygon vertices (pixel coords), with padding.

    Returns None if zones is empty (caller should run full-frame detection).
    """
    if not zones:
        return None
    xs: list[float] = []
    ys: list[float] = []
    for z in zones:
        for p in z.points:
            xs.append(float(p[0]) * frame_w)
            ys.append(float(p[1]) * frame_h)
    if not xs:
        return None
    x1, x2 = min(xs), max(xs)
    y1, y2 = min(ys), max(ys)
    bw = max(x2 - x1, 1.0)
    bh = max(y2 - y1, 1.0)
    px = bw * padding_frac
    py = bh * padding_frac
    x1o = int(max(0.0, x1 - px))
    y1o = int(max(0.0, y1 - py))
    x2o = int(min(float(frame_w), x2 + px))
    y2o = int(min(float(frame_h), y2 + py))
    # Ensure at least 2px width/height for valid crop (degenerate polygons / single vertex).
    if x2o <= x1o:
        x2o = min(frame_w, x1o + 2)
    if y2o <= y1o:
        y2o = min(frame_h, y1o + 2)
    if x2o - x1o < 2:
        x2o = min(frame_w, x1o + 2)
    if y2o - y1o < 2:
        y2o = min(frame_h, y1o + 2)
    if x2o <= x1o or y2o <= y1o:
        return None
    return (x1o, y1o, x2o, y2o)


class YoloTracker:
    def __init__(self, weights: str, person_class_id: int, plate_class_ids: list[int]) -> None:
        self.model = YOLO(weights)
        self.person_class_id = person_class_id
        self.plate_class_ids = set(plate_class_ids)

    def track_frame(
        self,
        bgr: np.ndarray,
        roi: tuple[int, int, int, int] | None = None,
    ) -> tuple[list[TrackedObject], list[TrackedObject]]:
        """
        Returns (plate_tracks, person_detections) in full-frame pixel coordinates.

        If roi is (x1, y1, x2, y2), runs detection on that crop and maps boxes back.
        If roi is None, runs on the full frame.
        """
        h, w = bgr.shape[:2]
        ox, oy = 0, 0
        infer = bgr
        if roi is not None:
            x1, y1, x2, y2 = roi
            x1 = max(0, min(x1, w - 1))
            y1 = max(0, min(y1, h - 1))
            x2 = max(x1 + 2, min(x2, w))
            y2 = max(y1 + 2, min(y2, h))
            infer = bgr[y1:y2, x1:x2]
            if infer.size == 0 or infer.shape[0] < 2 or infer.shape[1] < 2:
                infer = bgr
            else:
                ox, oy = x1, y1

        results = self.model.track(
            infer,
            persist=True,
            tracker="bytetrack.yaml",
            verbose=False,
        )
        plates: list[TrackedObject] = []
        persons: list[TrackedObject] = []
        if not results:
            return plates, persons
        r0 = results[0]
        if r0.boxes is None or len(r0.boxes) == 0:
            return plates, persons
        xyxy = r0.boxes.xyxy.cpu().numpy()
        conf = r0.boxes.conf.cpu().numpy()
        cls = r0.boxes.cls.cpu().numpy().astype(int)
        tid = r0.boxes.id
        if tid is None:
            tid_np = np.arange(len(xyxy), dtype=np.int64)
        else:
            tid_np = tid.cpu().numpy().astype(np.int64)
        for i in range(len(xyxy)):
            c = int(cls[i])
            box = (
                float(xyxy[i][0] + ox),
                float(xyxy[i][1] + oy),
                float(xyxy[i][2] + ox),
                float(xyxy[i][3] + oy),
            )
            tr = TrackedObject(
                track_id=int(tid_np[i]),
                cls_id=c,
                xyxy=box,
                conf=float(conf[i]),
            )
            if c == self.person_class_id:
                persons.append(tr)
            elif c in self.plate_class_ids:
                plates.append(tr)
        return plates, persons
