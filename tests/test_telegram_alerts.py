from collections import deque
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np

from app.cameras.gestion_camaras import DetectionService, GestionCamara, TelegramAlertService


class FakeDetector:
    def __init__(self, result):
        self.result = result

    def detect(self, _image):
        return self.result


class FakeAlertService:
    def __init__(self):
        self.sent = []

    def send_async(self, camera_name, alert_frame, now):
        self.sent.append((camera_name, alert_frame, now))


def make_face_result(score=0.9):
    bbox = SimpleNamespace(origin_x=100, origin_y=80, width=80, height=80)
    category = SimpleNamespace(score=score)
    detection = SimpleNamespace(categories=[category], bounding_box=bbox)
    return SimpleNamespace(detections=[detection])


def make_pose_result():
    return SimpleNamespace(pose_landmarks=[])


def make_detection_service(skip_frames=2):
    service = DetectionService.__new__(DetectionService)
    service.skip_frames = skip_frames
    service.ia_interval = 0.0
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


def make_camera(detection_service, alert_service):
    camera = GestionCamara.__new__(GestionCamara)
    camera.nombre = "pasillo"
    camera.alarm_enabled = True
    camera.stream_reader = SimpleNamespace(
        ret=True,
        frame=np.zeros((480, 640, 3), dtype=np.uint8),
    )
    camera.detection_service = detection_service
    camera.alert_service = alert_service
    return camera


class TelegramAlertsTest(unittest.TestCase):
    def test_processed_frame_sends_alert_while_detection_stays_active_on_skipped_frame(self):
        alert_service = FakeAlertService()
        camera = make_camera(make_detection_service(skip_frames=2), alert_service)

        for _ in range(5):
            camera.get_processed_frame()

        self.assertEqual(len(alert_service.sent), 2)
        self.assertEqual(alert_service.sent[-1][0], "pasillo")

    def test_photo_worker_sends_jpg_to_telegram_with_caption(self):
        service = TelegramAlertService.__new__(TelegramAlertService)
        service.bot = Mock()
        service.chat_id = "chat-id"
        frame = np.zeros((80, 80, 3), dtype=np.uint8)

        with patch("builtins.print"):
            service._send_photo_worker("pasillo", frame)

        service.bot.sendPhoto.assert_called_once()
        chat_id, photo = service.bot.sendPhoto.call_args.args
        self.assertEqual(chat_id, "chat-id")
        self.assertTrue(hasattr(photo, "read"))
        self.assertEqual(
            service.bot.sendPhoto.call_args.kwargs["caption"],
            "Intruder detected on pasillo",
        )


if __name__ == "__main__":
    unittest.main()
