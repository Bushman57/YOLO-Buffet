"""Offline metrics: multi-label F1, detection P/R (greedy IoU)."""

from __future__ import annotations

import numpy as np

try:
    from sklearn.metrics import f1_score
except ImportError:
    f1_score = None  # type: ignore[misc, assignment]


def multilabel_f1(y_true: np.ndarray, y_pred: np.ndarray, average: str = "macro") -> float:
    """y_true, y_pred shape (n_samples, n_labels) binary."""
    if f1_score is None:
        raise RuntimeError("Install scikit-learn: pip install scikit-learn")
    return float(f1_score(y_true, y_pred, average=average, zero_division=0))


def detection_precision_recall(
    pred_boxes: list[tuple[float, float, float, float]],
    gt_boxes: list[tuple[float, float, float, float]],
    iou_threshold: float = 0.5,
) -> tuple[float, float]:
    """Greedy IoU match; returns (precision, recall)."""
    if not pred_boxes and not gt_boxes:
        return 1.0, 1.0
    if not pred_boxes:
        return 0.0, 0.0
    if not gt_boxes:
        return 0.0, 0.0

    def iou(a, b) -> float:
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

    matched_gt: set[int] = set()
    tp = 0
    for pb in pred_boxes:
        best_j = -1
        best_iou = 0.0
        for j, gb in enumerate(gt_boxes):
            if j in matched_gt:
                continue
            v = iou(pb, gb)
            if v > best_iou:
                best_iou = v
                best_j = j
        if best_j >= 0 and best_iou >= iou_threshold:
            tp += 1
            matched_gt.add(best_j)

    fp = len(pred_boxes) - tp
    fn = len(gt_boxes) - tp
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return precision, recall


def event_time_accuracy(
    pred_times_sec: list[float],
    gt_times_sec: list[float],
    tolerance_sec: float = 2.0,
) -> tuple[float, int, int]:
    """
    Match each prediction to at most one ground-truth within tolerance (seconds).
    Returns (accuracy, true_positives, len(gt_times)).
    """
    if not gt_times_sec:
        return (1.0 if not pred_times_sec else 0.0, 0, 0)
    gt = sorted(gt_times_sec)
    pr = sorted(pred_times_sec)
    used_gt: set[int] = set()
    tp = 0
    for p in pr:
        best_i = -1
        best_d = tolerance_sec + 1.0
        for i, g in enumerate(gt):
            if i in used_gt:
                continue
            d = abs(p - g)
            if d <= tolerance_sec and d < best_d:
                best_d = d
                best_i = i
        if best_i >= 0:
            tp += 1
            used_gt.add(best_i)
    acc = tp / len(gt_times_sec)
    return acc, tp, len(gt_times_sec)
