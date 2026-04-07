import uuid

from worker.detection import TrackedObject
from worker.events import ServingEventEngine, ZoneSpec


def test_event_emits_after_dwell_and_exit():
    cam = uuid.uuid4()
    zones = [ZoneSpec(zone_id=uuid.uuid4(), points=[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])]
    eng = ServingEventEngine(cam, zones, dwell_seconds=0.05, require_person_near_plate=False)
    pl = TrackedObject(track_id=1, cls_id=45, xyxy=(40.0, 40.0, 60.0, 60.0), conf=0.9)
    persons: list = []
    pending = eng.process_frame(100, 100, 1000.0, [pl], persons)
    assert pending == []
    pending = eng.process_frame(100, 100, 1000.06, [pl], persons)
    assert pending == []
    pending = eng.process_frame(100, 100, 1000.07, [], [])
    assert len(pending) == 1
    assert pending[0].plate_track_id == 1
    assert pending[0].camera_id == cam
