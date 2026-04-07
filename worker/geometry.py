"""Zone geometry helpers (normalized coordinates 0–1)."""


def point_in_polygon(x: float, y: float, points: list[list[float]]) -> bool:
    """Ray casting; points are [[nx, ny], ...] in image-normalized space."""
    n = len(points)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = points[i][0], points[i][1]
        xj, yj = points[j][0], points[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def bbox_center_norm(xyxy: tuple[float, float, float, float], w: int, h: int) -> tuple[float, float]:
    x1, y1, x2, y2 = xyxy
    cx = ((x1 + x2) / 2) / max(w, 1)
    cy = ((y1 + y2) / 2) / max(h, 1)
    return cx, cy


def iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def any_person_near_plate(
    plate_xyxy: tuple[float, float, float, float],
    person_boxes: list[tuple[float, float, float, float]],
    min_iou: float = 0.01,
) -> bool:
    for pb in person_boxes:
        if iou(plate_xyxy, pb) >= min_iou:
            return True
        if _centroid_dist(plate_xyxy, pb) < _diag(plate_xyxy) * 1.5:
            return True
    return False


def _centroid_dist(
    a: tuple[float, float, float, float], b: tuple[float, float, float, float]
) -> float:
    acx = (a[0] + a[2]) / 2
    acy = (a[1] + a[3]) / 2
    bcx = (b[0] + b[2]) / 2
    bcy = (b[1] + b[3]) / 2
    return ((acx - bcx) ** 2 + (acy - bcy) ** 2) ** 0.5


def _diag(xyxy: tuple[float, float, float, float]) -> float:
    return ((xyxy[2] - xyxy[0]) ** 2 + (xyxy[3] - xyxy[1]) ** 2) ** 0.5
