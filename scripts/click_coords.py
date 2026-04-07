#!/usr/bin/env python3
"""Open a video frame; left-click prints (x, y). Match W/H with pixels_to_zone_json."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        epilog="Example: python scripts/click_coords.py video_samples/BATCH_101.mp4 --frame 120",
    )
    p.add_argument(
        "video",
        nargs="?",
        default="video_samples/BATCH_101.mp4",
        type=Path,
        help="Path to video file (default: video_samples/BATCH_101.mp4)",
    )
    p.add_argument(
        "--frame",
        type=int,
        default=0,
        help="Zero-based frame index to load (default: 0 = first frame)",
    )
    args = p.parse_args()
    path = args.video.resolve()
    if not path.is_file():
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        return 2

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        print(f"ERROR: cannot open video: {path}", file=sys.stderr)
        return 2

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Video: {path.name}")
    print(f"CAP_PROP size: W={w} H={h} (use with pixels_to_zone_json.py --width {w} --height {h})")

    if args.frame > 0:
        cap.set(cv2.CAP_PROP_POS_FRAMES, float(args.frame))

    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        print("ERROR: could not read frame", file=sys.stderr)
        return 2

    fh, fw = frame.shape[:2]
    if fw != w or fh != h:
        print(f"Note: decoded frame shape {fw}x{fh} (may differ from CAP_PROP on some files)")

    def on_mouse(event, x, y, flags, param) -> None:
        if event == cv2.EVENT_LBUTTONDOWN:
            print(f"x={x}, y={y}")

    win = "click_coords — left-click prints x,y — q to quit"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(win, on_mouse)

    print("Left-click on the image to print coordinates. Press q to quit.")
    while True:
        cv2.imshow(win, frame)
        k = cv2.waitKey(1) & 0xFF
        if k == ord("q"):
            break
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
