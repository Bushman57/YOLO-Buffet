"""YOLO + ByteTrack smoke test on a blank frame (downloads weights on first run)."""

import numpy as np
import pytest

from worker.detection import YoloTracker


@pytest.mark.slow
def test_tracker_runs_on_blank_frame():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    t = YoloTracker("yolov8n.pt", person_class_id=0, plate_class_ids=[45])
    plates, persons = t.track_frame(frame)
    assert isinstance(plates, list)
    assert isinstance(persons, list)
