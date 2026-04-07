import numpy as np

from shared.metrics_eval import detection_precision_recall, event_time_accuracy, multilabel_f1


def test_multilabel_f1():
    y_true = np.array([[1, 0], [0, 1]])
    y_pred = np.array([[1, 0], [0, 1]])
    assert multilabel_f1(y_true, y_pred) > 0.99


def test_detection_pr():
    p, r = detection_precision_recall([(0, 0, 1, 1)], [(0, 0, 1, 1)])
    assert p == 1.0 and r == 1.0


def test_event_time_accuracy():
    acc, tp, n = event_time_accuracy([10.0], [10.1], tolerance_sec=0.5)
    assert acc == 1.0 and tp == 1 and n == 1
