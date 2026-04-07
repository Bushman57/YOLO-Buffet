"""Tests for zone union ROI (no Ultralytics load)."""

import uuid

from worker.detection import zone_union_roi_pixels
from worker.events import ZoneSpec


def test_zone_union_roi_pixels_empty():
    assert zone_union_roi_pixels([], 1920, 1080, 0.15) is None


def test_zone_union_roi_pixels_padded():
    zid = uuid.uuid4()
    z = ZoneSpec(zone_id=zid, points=[[0.5, 0.5], [0.6, 0.5], [0.6, 0.6], [0.5, 0.6]])
    roi = zone_union_roi_pixels([z], 1000, 800, padding_frac=0.1)
    assert roi is not None
    x1, y1, x2, y2 = roi
    assert x1 == 490 and x2 == 610 and y1 == 392 and y2 == 488


def test_zone_union_roi_pixels_single_point():
    zid = uuid.uuid4()
    z = ZoneSpec(zone_id=zid, points=[[0.1, 0.2]])
    roi = zone_union_roi_pixels([z], 100, 100, 0.5)
    assert roi is not None
    x1, y1, x2, y2 = roi
    assert x2 > x1 and y2 > y1
    assert 0 <= x1 < x2 <= 100 and 0 <= y1 < y2 <= 100


def test_zone_union_two_zones_union():
    a = ZoneSpec(zone_id=uuid.uuid4(), points=[[0.0, 0.0], [0.1, 0.0], [0.1, 0.1], [0.0, 0.1]])
    b = ZoneSpec(zone_id=uuid.uuid4(), points=[[0.9, 0.9], [1.0, 0.9], [1.0, 1.0], [0.9, 1.0]])
    roi = zone_union_roi_pixels([a, b], 100, 100, padding_frac=0.0)
    assert roi == (0, 0, 100, 100)
