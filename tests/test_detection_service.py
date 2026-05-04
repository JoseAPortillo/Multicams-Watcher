from collections import deque
from types import SimpleNamespace
import unittest

import numpy as np

from app.cameras.gestion_camaras import DetectionService


class FakeDetector:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def detect(self, _image):
        self.calls += 1
        return self.result


def make_face_result(score=0.9):
    bbox = SimpleNamespace(origin_x=100, origin_y=80, width=80, height=80)
    category = SimpleNamespace(score=score)
    detection = SimpleNamespace(categories=[category], bounding_box=bbox)
    return SimpleNamespace(detections=[detection])


def make_pose_result(has_pose=False):
    landmarks = [SimpleNamespace(x=0.5, y=0.5) for _ in range(8)] if has_pose else []
    return SimpleNamespace(pose_landmarks=[landmarks] if has_pose else [])


def make_detection_service(skip_frames=2, ia_interval=0.0):
    service = DetectionService.__new__(DetectionService)
    service.skip_frames = skip_frames
    service.ia_interval = ia_interval
    service.frame_count = 0
    service.last_ia_time = 0.0
    service.min_face_confidence = 0.5
    service.min_face_size = 40
    service.history = deque(maxlen=5)
    service.min_positive_frames = 2
    service.last_active_detection = False
    service.face_detector = FakeDetector(make_face_result())
    service.pose_detector = FakeDetector(make_pose_result())
    return service


class DetectionServiceTest(unittest.TestCase):
    def test_keeps_active_detection_on_skipped_frames(self):
        service = make_detection_service(skip_frames=2)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        _, active_1 = service.annotate(frame)
        _, active_2 = service.annotate(frame)
        _, active_3 = service.annotate(frame)
        _, active_4 = service.annotate(frame)
        _, active_5 = service.annotate(frame)

        self.assertFalse(active_1)
        self.assertFalse(active_2)
        self.assertFalse(active_3)
        self.assertTrue(active_4)
        self.assertTrue(active_5)
        self.assertEqual(service.face_detector.calls, 2)


if __name__ == "__main__":
    unittest.main()
