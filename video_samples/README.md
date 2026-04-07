# Batch video samples (Phase 1–2 testing)

Use a **folder** of ten short clips so the worker runs them **in order** with a **fresh YOLO/ByteTrack tracker and event FSM per clip** (no track or state leakage across files).

## Naming (required)

Place **exactly ten** files in one directory:

| Clip ID   | Filename pattern (extension optional) |
| --------- | ------------------------------------- |
| `BATCH_101` … `BATCH_110` | `BATCH_101`, `BATCH_102`, … `BATCH_110` |

Allowed extensions (case-insensitive): `.mp4`, `.avi`, `.mov`, `.mkv`.

Examples: `BATCH_101.mp4`, `BATCH_110.MKV`.

All ten indices **must** be present; missing or duplicate indices cause a clear error at startup.

## Configure the worker

Point `VIDEO_SOURCE` at the **directory** (not an individual file):

```text
VIDEO_SOURCE=C:\Users\you\project\video_samples
```

On Windows PowerShell:

```powershell
$env:VIDEO_SOURCE = "C:\Users\savin\Desktop\Taistat\Buffei_YOLO\video_samples"
```

Optional: cap frames **per clip** for quick smoke runs:

```text
WORKER_MAX_FRAMES=300
```

## Heartbeats and Neon

While processing a batch clip, camera heartbeats may include a `notes` field like `batch=BATCH_107` for traceability in the database.

## Baseline local file (reference run)

Wall-clock time from the **`Batch clip …`** log line to **`Finished batch clip …`** for each file (full pipeline: ingest, YOLO/ByteTrack, event engine, DB heartbeats, optional classifier). **Frames** are from the same log line (`Finished batch clip BATCH_10n frames=N`). One recorded run on **2026-04-04**, local Windows machine, `VIDEO_SOURCE` = project `video_samples` directory.

| Clip | Baseline local file (wall-clock) | Frames | Video file length |
| ---- | -------------------------------- | ------ | ----------------- |
| `BATCH_101` | 4:24 (~264 s) | 1095 | 01:12 |
| `BATCH_102` | 1:53 (~113 s) | 450 | 00:29 |
| `BATCH_103` | 3:40 (~220 s) | 915 | 01:00 |
| `BATCH_104` | 3:44 (~223 s) | 930 | 01:01 |
| `BATCH_105` | 3:47 (~227 s) | 915 | 01:00 |
| `BATCH_106` | 2:02 (~122 s) | 465 | 00:30 |
| `BATCH_107` | 1:53 (~113 s) | 375 | 00:25 |
| `BATCH_108` | 1:51 (~111 s) | 420 | 00:28 |
| `BATCH_109` | 2:05 (~125 s) | 510 | 00:33 |
| `BATCH_110` | 3:32 (~212 s) | 810 | 00:53 |

**Video file length** is source media duration (mm:ss) for comparison. Wall-clock processing time is **not** equal to that duration: it depends on `TARGET_FPS`, GPU/CPU, DB latency, and model load.

## Phase 2 checklist (suggested)

- [ ] All ten files present and named correctly (`python scripts/verify_batch_samples.py`).
- [ ] `WORKER_CAMERA_ID` set to a seeded camera; `DATABASE_URL` valid.
- [ ] Run `python -m worker` and confirm logs show each `BATCH_10n` in order.
- [ ] Inspect events / heartbeats for expected behavior per clip.

## Phase 3: Serving zone calibration (fixed buffet angle)

The worker treats the **video frame as a 2D image**: serving zones are polygons in **normalized coordinates** (0–1). A high, fixed camera angle (buffet region drawn as a trapezoid or rectangle on screen) maps directly to that polygon—no separate 3D model in code. The plate must be **detected** and its bbox **center** must fall **inside** the polygon; optional **person-near-plate** rules apply (see `worker/events.py`, `worker/geometry.py`).

### Reference frame

1. Export **one still** from a clip in this folder (or from a live grab) that matches how you will run in production: same **resolution** and **aspect ratio** as the RTSP or batch files you care about.
2. Note **frame width** and **height** in pixels (e.g. from ffprobe or the player).

### From buffet region to `geometry.points`

1. Trace the buffet area (e.g. the four corners of your on-screen quadrilateral) in **pixel coordinates** `(x, y)` in order around the polygon (clockwise or counterclockwise is fine).
2. Convert each corner: `nx = x / frame_width`, `ny = y / frame_height`.
3. Store in Neon via the API: `geometry` must contain **`points`**: `[[nx, ny], ...]`.

Use **`python scripts/pixels_to_zone_json.py`** to avoid manual math: pass `--width`, `--height`, and corner coordinates `x1 y1 x2 y2 ...`.

To **pick pixel coordinates** from a clip, run **`python scripts/click_coords.py path/to/clip.mp4`** (optional `--frame N`); left-click prints `x,y` and the script prints the frame size to use with `pixels_to_zone_json.py`.

### Example `POST /cameras/{camera_id}/zones` body

Start the API (`uvicorn app.main:app`), open **`/docs`**, authorize if needed, then POST:

```json
{
  "zone_type": "serving",
  "geometry": {
    "points": [
      [0.1, 0.15],
      [0.55, 0.12],
      [0.58, 0.45],
      [0.12, 0.48]
    ]
  }
}
```

Replace the numbers with output from `pixels_to_zone_json.py` for your reference frame.

Each **`POST /zones`** creates a **new** row. If you calibrated twice, **`GET /cameras/{id}/zones`** will list multiple zones and the preview draws **all** of them. Remove a stale zone with **`DELETE /cameras/{camera_id}/zones/{zone_id}`** in Swagger (use the `id` from the zone you no longer want).

### Tuning order

1. **Zone shape** — Cover the buffet surface; start generous, then tighten. If **no zones** exist for the camera, the engine treats the whole frame as “in zone” (see `worker/events.py`), which is only useful for debugging dwell/person rules.
2. **`SERVE_DWELL_SECONDS`** — Start low (e.g. `0.5`–`1.0`) until `GET /events` returns rows; increase toward production.
3. **`REQUIRE_PERSON_NEAR_PLATE`** — If plates fire but events do not, try `false` temporarily to confirm zone + dwell; then set `true` again and **widen** the polygon slightly toward the customer side so person and plate boxes satisfy the proximity heuristic.

### Live RTSP vs batch clips

Use the **same** `geometry` JSON for both when the camera mount and **output resolution** match. If batch exports use a **different resolution or crop** than live, re-measure corners on a frame from **that** source or zones will misalign.

### Validate

Run `python -m worker` with `VIDEO_SOURCE` pointing at this directory (or live URL), then **`GET /events?camera_id=<uuid>`** in Swagger. Iterate polygon and env vars until `serving_events` look correct.

### Debug preview (optional)

Set **`WORKER_PREVIEW=imshow`** in `.env` to show an OpenCV window with **cyan** zone outlines and **green/orange** person/plate boxes on each processed frame (same detections the event engine uses). Default is **`off`**. Use on a machine with a display; headless environments will log a one-time warning.

### YOLO ROI crop (small plates)

When serving **zones** exist, the worker can **crop** to the axis-aligned union of zone vertices plus padding before running YOLO, then map boxes back to the full frame (`worker/detection.py`). Set **`YOLO_ROI_CROP=true`** (default) and **`YOLO_ROI_PADDING_FRAC`** (e.g. `0.15`) in `.env`. Set **`YOLO_ROI_CROP=false`** to use the full frame only. Persons **outside** the crop are not detected; increase padding if `REQUIRE_PERSON_NEAR_PLATE` needs people beside the counter.

## Do not commit large binaries

Copy your own test videos into this folder locally; keep them out of git if they are large or sensitive.
