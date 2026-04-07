"""Tests for worker preview overlay drawing (no GUI)."""

import uuid

import numpy as np
import pytest

from worker.detection import TrackedObject
from worker.events import ZoneSpec
from worker.preview import PreviewEventFeed, draw_overlays


def test_draw_overlays_preserves_input_frame():
    frame = np.zeros((100, 200, 3), dtype=np.uint8)
    before = frame.copy()
    zid = uuid.uuid4()
    zones = [
        ZoneSpec(
            zone_id=zid,
            points=[[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]],
        )
    ]
    plates: list[TrackedObject] = []
    persons: list[TrackedObject] = []
    out = draw_overlays(frame, plates, persons, zones, 200, 100)
    np.testing.assert_array_equal(frame, before)
    assert out.shape == frame.shape
    assert not np.array_equal(out, before)


def test_draw_overlays_event_lines_overlay():
    frame = np.zeros((80, 200, 3), dtype=np.uint8)
    out = draw_overlays(frame, [], [], [], 200, 80, event_lines=["evt abcdef01 T3 1200ms rice"])
    assert out.sum() > 0


def test_preview_event_feed_ttl():
    feed = PreviewEventFeed(max_lines=3, ttl_sec=1.0)
    feed.add(100.0, "a")
    feed.add(100.5, "b")
    assert len(feed.lines(100.5)) == 2
    assert feed.lines(102.1) == []


def test_draw_overlays_boxes_and_zones_change_pixels():
    frame = np.zeros((120, 160, 3), dtype=np.uint8)
    zid = uuid.uuid4()
    zones = [ZoneSpec(zone_id=zid, points=[[0.0, 0.0], [0.5, 0.0], [0.5, 0.5], [0.0, 0.5]])]
    plates = [
        TrackedObject(track_id=7, cls_id=45, xyxy=(10.0, 10.0, 40.0, 40.0), conf=0.95)
    ]
    persons = [
        TrackedObject(track_id=1, cls_id=0, xyxy=(60.0, 60.0, 100.0, 100.0), conf=0.88)
    ]
    out = draw_overlays(frame, plates, persons, zones, 160, 120)
    assert out.sum() > 0


def test_settings_worker_preview_literal():
    from pydantic import ValidationError

    from shared.config import Settings

    s = Settings(worker_preview="imshow")
    assert s.worker_preview == "imshow"
    s2 = Settings(worker_preview="OFF")
    assert s2.worker_preview == "off"

    with pytest.raises(ValidationError):
        Settings(worker_preview="invalid")
