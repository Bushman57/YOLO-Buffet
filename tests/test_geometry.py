from worker.geometry import bbox_center_norm, iou, point_in_polygon


def test_point_in_square():
    square = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
    assert point_in_polygon(0.5, 0.5, square)
    assert not point_in_polygon(1.5, 0.5, square)


def test_bbox_center_norm():
    cx, cy = bbox_center_norm((0.0, 0.0, 100.0, 50.0), 100, 50)
    assert abs(cx - 0.5) < 1e-6
    assert abs(cy - 0.5) < 1e-6


def test_iou_overlap():
    a = (0.0, 0.0, 10.0, 10.0)
    b = (5.0, 5.0, 15.0, 15.0)
    assert iou(a, b) > 0.1
