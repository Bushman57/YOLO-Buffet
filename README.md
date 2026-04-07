# Buffet MVP

Python stack: **FastAPI**, **Neon (Postgres)**, **OpenCV**, **Ultralytics YOLOv8** + **ByteTrack**, multi-label classifier.

## Setup

1. Copy `.env.example` to `.env` and set `DATABASE_URL` (Neon connection string with `postgresql+asyncpg://`).

2. Install and migrate:

```bash
pip install -e ".[dev]"
alembic upgrade head
```

3. Seed demo org/site/camera (optional):

```bash
python scripts/seed_demo.py
```

4. Run API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

5. Run worker (needs a camera row and `VIDEO_SOURCE` or `camera.rtsp_url`):

```bash
set WORKER_CAMERA_ID=<uuid from seed>
set VIDEO_SOURCE=C:\path\to\video.mp4
set REQUIRE_PERSON_NEAR_PLATE=false
python -m worker
```

### Live RTSP + imshow (calibration / ops)

1. **Neon**: Ensure the camera row has a valid **`rtsp_url`** (and optional FPS). Create **serving zones** for that camera (`POST /cameras/{id}/zones`) so the event engine and optional YOLO ROI make sense.
2. **Env**: Set **`WORKER_CAMERA_ID`** to that camera’s UUID. Leave **`VIDEO_SOURCE` empty** so the worker reads **`camera.rtsp_url`**, or set **`VIDEO_SOURCE=rtsp://...`** explicitly. Set **`WORKER_PREVIEW=imshow`** for a local OpenCV window. Tune **`TARGET_FPS`**, **`SERVE_DWELL_SECONDS`**, **`REQUIRE_PERSON_NEAR_PLATE`** as needed.
3. **Display**: Run `python -m worker` on a machine with a desktop (headless servers will log a warning and skip the window).

The preview shows zones (cyan), person boxes (green), plate boxes (orange), and a **rolling list of persisted serving events** (event id prefix, plate track id, dwell ms, optional classifier labels) at the top-left. **`INFO` logs** also print each commit. For dashboards or scripts, poll **`GET /events`** while the API is running.

### Batch video testing (Phase 2)

For repeatable validation on ten short files, put **`BATCH_101` … `BATCH_110`** (`.mp4`/`.avi`/`.mov`/`.mkv`) in one folder and set `VIDEO_SOURCE` to that **directory**. The worker processes clips in order and creates a **new** YOLO/ByteTrack tracker and event engine for each clip so track IDs and FSM state do not carry over.

Example:

```powershell
set VIDEO_SOURCE=C:\Users\savin\Desktop\Taistat\Buffei_YOLO\video_samples
set WORKER_MAX_FRAMES=300
python -m worker
```

`WORKER_MAX_FRAMES` applies **per clip** in directory mode. Naming rules, a checklist, and an optional **baseline local file** timing table (wall-clock, frame counts, and source video length) are in [`video_samples/README.md`](video_samples/README.md). Use `python scripts/verify_batch_samples.py` to confirm all ten files are present before running.

**Debug preview (Phase 3 / ops):** set `WORKER_PREVIEW=imshow` in `.env` to open a local OpenCV window with serving zones, plate/person boxes, and recent **serving event** lines (default `off`). Requires a display; not for headless servers.

## Endpoints

- `GET /health` — liveness
- `GET /ready` — DB connectivity
- `GET /sites/organizations`, `GET /sites`
- `GET /cameras`, `GET /cameras/{id}/zones`, `POST /cameras/{id}/zones`, `DELETE /cameras/{id}/zones/{zone_id}`
- `GET /events`, `GET /events/{id}`

## Tests

```bash
pytest
```

Optional slow test (downloads YOLO weights): `pytest tests/test_tracking_smoke.py -m slow`

## Evaluation and load smoke

```bash
python scripts/evaluate.py
python scripts/smoke_load.py
```

(Start the API first for `smoke_load.py`, or set `API_BASE_URL`.)
