"""
Offline evaluation: detection P/R, multi-label F1 (see shared.metrics_eval).

Usage:
  python -m scripts.evaluate
"""

from __future__ import annotations

import numpy as np

from shared.metrics_eval import (
    detection_precision_recall,
    event_time_accuracy,
    multilabel_f1,
)


def demo() -> None:
    y_true = np.array([[1, 0, 1], [0, 1, 1]])
    y_pred = np.array([[1, 0, 0], [0, 1, 1]])
    f1 = multilabel_f1(y_true, y_pred)
    print("demo multilabel macro-F1:", f1)
    p, r = detection_precision_recall([(0, 0, 10, 10)], [(0, 0, 10, 10)])
    print("demo detection precision, recall:", p, r)
    acc, tp, n = event_time_accuracy([1.0, 5.2], [1.1, 5.0], tolerance_sec=0.5)
    print("demo event time accuracy:", acc, "tp", tp, "gt", n)


if __name__ == "__main__":
    demo()
