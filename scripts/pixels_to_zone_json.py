#!/usr/bin/env python3
"""Convert pixel corner coordinates to normalized zone geometry JSON for POST /cameras/{id}/zones."""

from __future__ import annotations

import argparse
import json
import sys


def main() -> int:
    p = argparse.ArgumentParser(
        description=(
            "Convert polygon corners in pixel space to geometry.points (0-1 normalized). "
            "Pass corners as x1 y1 x2 y2 ... in order around the polygon."
        )
    )
    p.add_argument("--width", type=int, required=True, help="Frame width in pixels")
    p.add_argument("--height", type=int, required=True, help="Frame height in pixels")
    p.add_argument(
        "coords",
        nargs="+",
        type=float,
        help="Corner coordinates: x1 y1 x2 y2 ... (pairs)",
    )
    p.add_argument(
        "--zone-type",
        default="serving",
        help='zone_type field (default: serving)',
    )
    args = p.parse_args()

    if len(args.coords) % 2 != 0:
        print("ERROR: need an even number of values (x y pairs)", file=sys.stderr)
        return 2

    w, h = args.width, args.height
    if w <= 0 or h <= 0:
        print("ERROR: width and height must be positive", file=sys.stderr)
        return 2

    points: list[list[float]] = []
    for i in range(0, len(args.coords), 2):
        x, y = args.coords[i], args.coords[i + 1]
        points.append([round(x / w, 6), round(y / h, 6)])

    body = {
        "zone_type": args.zone_type,
        "geometry": {"points": points},
    }
    print(json.dumps(body, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
