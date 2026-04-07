"""Worker entrypoint: ingest → YOLO/ByteTrack → events → optional classification."""

from __future__ import annotations

import asyncio
import logging
import sys
import uuid
from datetime import datetime, timezone
from sqlalchemy import select

from shared.config import get_settings
from shared.db.session import async_session_factory
from shared.models.tables import Camera
from worker.batch_sources import resolve_worker_sources
from worker.classify import ClassifierRuntime, crop_plate
from worker.db_ops import (
    commit_serving_event_and_classification,
    fetch_camera,
    fetch_zones,
    get_or_create_default_model_version,
    upsert_heartbeat,
)
from worker.detection import YoloTracker, zone_union_roi_pixels
from worker.events import PendingEvent, ServingEventEngine
from worker.ingest import VideoSource
from worker.preview import PreviewEventFeed, draw_overlays, imshow_frame

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


def _preview_event_line(
    event_id: uuid.UUID,
    ev: PendingEvent,
    labels_payload: dict | None,
) -> str:
    parts = [f"evt {str(event_id)[:8]}", f"T{ev.plate_track_id}", f"{ev.dwell_ms}ms"]
    if labels_payload and labels_payload.get("above_threshold"):
        parts.append(",".join(sorted(labels_payload["above_threshold"].keys())))
    return " ".join(parts)


async def _resolve_camera(session) -> Camera | None:
    settings = get_settings()
    if settings.worker_camera_id:
        try:
            cid = uuid.UUID(settings.worker_camera_id)
        except ValueError:
            logger.error("Invalid WORKER_CAMERA_ID")
            return None
        return await fetch_camera(session, cid)
    q = await session.execute(select(Camera).limit(1))
    return q.scalar_one_or_none()


def _resolve_video_jobs(settings, cam: Camera) -> list[tuple[str, str | None]]:
    """Returns list of (source_path_or_url, batch_label_or_none)."""
    vs = (settings.video_source or "").strip()
    if vs:
        return resolve_worker_sources(vs)
    if cam.rtsp_url:
        return [(cam.rtsp_url, None)]
    raise RuntimeError("Set VIDEO_SOURCE or camera.rtsp_url")


async def run_async() -> None:
    settings = get_settings()

    async def setup():
        factory = async_session_factory()
        async with factory() as session:
            cam = await _resolve_camera(session)
            if cam is None:
                raise RuntimeError("No camera in DB — seed a site/camera or set WORKER_CAMERA_ID.")
            zones = await fetch_zones(session, cam.id)
            mv_id = await get_or_create_default_model_version(session, "default_mvp")
            return cam, zones, mv_id

    cam, zones, model_version_id = await setup()
    jobs = _resolve_video_jobs(settings, cam)
    labels = settings.classifier_label_list()
    clf = ClassifierRuntime(labels, settings.classifier_checkpoint)
    max_frames = settings.worker_max_frames

    for job_idx, (source_str, batch_label) in enumerate(jobs, start=1):
        if batch_label:
            logger.info(
                "Batch clip %s/%s: %s path=%s",
                job_idx,
                len(jobs),
                batch_label,
                source_str,
            )
        else:
            logger.info("Starting worker for camera %s source=%s", cam.id, source_str)

        video = VideoSource(source_str, target_fps=settings.target_fps or cam.fps_target)
        tracker = YoloTracker(
            settings.yolo_weights,
            settings.yolo_person_class_id,
            settings.plate_class_ids_list(),
        )
        engine = ServingEventEngine(
            camera_id=cam.id,
            zones=zones,
            dwell_seconds=settings.serve_dwell_seconds,
            require_person_near_plate=settings.require_person_near_plate,
        )

        frame_idx = 0
        hb_notes = f"batch={batch_label}" if batch_label else None
        roi_logged = False
        event_feed = PreviewEventFeed()

        try:
            for packet in video.frames():
                frame_idx += 1
                bgr = packet.bgr
                h, w = bgr.shape[:2]
                roi = None
                if settings.yolo_roi_crop and zones:
                    roi = zone_union_roi_pixels(zones, w, h, settings.yolo_roi_padding_frac)
                    if roi and not roi_logged:
                        logger.info(
                            "YOLO ROI crop x1,y1,x2,y2=%s padding_frac=%s",
                            roi,
                            settings.yolo_roi_padding_frac,
                        )
                        roi_logged = True
                plates, persons = tracker.track_frame(bgr, roi=roi)
                pending = engine.process_frame(w, h, packet.t_wall, plates, persons)

                if frame_idx % 30 == 0 or frame_idx == 1:
                    factory = async_session_factory()
                    async with factory() as session:
                        await upsert_heartbeat(
                            session,
                            cam.id,
                            frame_idx,
                            datetime.now(timezone.utc),
                            notes=hb_notes,
                        )

                for ev in pending:
                    labels_payload: dict | None = None
                    if not ev.bbox_snapshot.get("lost_track"):
                        xy = ev.bbox_snapshot.get("xyxy") or [0, 0, 1, 1]
                        xyxy = (float(xy[0]), float(xy[1]), float(xy[2]), float(xy[3]))
                        crop = crop_plate(bgr, xyxy)
                        probs = clf.predict_all_proba(crop)
                        thr = settings.classification_threshold
                        filtered = {k: v for k, v in probs.items() if v >= thr}
                        labels_payload = {"scores": probs, "above_threshold": filtered}

                    factory = async_session_factory()
                    async with factory() as session:
                        eid = await commit_serving_event_and_classification(
                            session, ev, model_version_id, labels_payload
                        )
                    logger.info(
                        "Serving event persisted id=%s plate_track=%s dwell_ms=%s",
                        eid,
                        ev.plate_track_id,
                        ev.dwell_ms,
                    )
                    if settings.worker_preview == "imshow":
                        event_feed.add(
                            packet.t_wall,
                            _preview_event_line(eid, ev, labels_payload),
                        )

                if settings.worker_preview == "imshow":
                    vis = draw_overlays(
                        bgr,
                        plates,
                        persons,
                        zones,
                        w,
                        h,
                        event_lines=event_feed.lines(packet.t_wall),
                    )
                    imshow_frame(vis)

                if max_frames is not None and frame_idx >= max_frames:
                    logger.info(
                        "Stopping clip after worker_max_frames=%s (per clip)",
                        max_frames,
                    )
                    break
        finally:
            video.release()

        if batch_label:
            logger.info("Finished batch clip %s frames=%s", batch_label, frame_idx)


def run() -> None:
    asyncio.run(run_async())


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        sys.exit(0)
