"""Capture, analysis, and control infrastructure for IP cameras.

This module defines the main ``GestionCamara`` facade and several internal,
specialized collaborators:

- ``StreamReader``: stream opening, reading, and reconnection.
- ``TelegramAlertService``: asynchronous photo delivery to Telegram.
- ``DetectionService``: person detection using MediaPipe.
- ``TapoController``: PTZ control for Tapo cameras.
- ``CameraHealthMonitor``: stream and PTZ health tracking.

The goal of this refactor is to move the implementation closer to SOLID by
separating responsibilities without breaking the public interface already used
by the rest of the project.
"""

import io
import os
import re
import socket
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import cv2
import mediapipe as mp
import requests
import telepot
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from pytapo import Tapo

from app.core.settings import FACE_MODEL_FILE, POSE_MODEL_FILE


@dataclass(frozen=True)
class StreamEndpoint:
    
    host: Optional[str]
    port: Optional[int]

    @classmethod
    def from_url(cls, url: str) -> "StreamEndpoint":
        parsed = urlparse(url)
        if parsed.port:
            port = parsed.port
        elif parsed.scheme == "rtsp":
            port = 554
        elif parsed.scheme == "http":
            port = 80
        else:
            port = None
        return cls(host=parsed.hostname, port=port)


class StreamReader:

    def __init__(self, url: str, retry_interval: float = 3.0):
        self.url = url
        self.endpoint = StreamEndpoint.from_url(url)
        self.retry_interval = retry_interval
        self.cap = None
        self.ret = False
        self.frame = None
        self.stopped = False
        self._last_open_try = 0.0
        self._thread = None

    def _quick_tcp_check(self, timeout: float = 0.8) -> bool:
        if not self.endpoint.host or not self.endpoint.port:
            return False
        try:
            with socket.create_connection((self.endpoint.host, int(self.endpoint.port)), timeout=timeout):
                return True
        except Exception:
            return False

    def _try_open_stream(self):
        now = time.time()
        if now - self._last_open_try < self.retry_interval:
            return
        self._last_open_try = now

        if not self._quick_tcp_check():
            self.ret = False
            return

        self.cap = cv2.VideoCapture(self.url)

    def _release_capture(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def update(self):
        while not self.stopped:
            if self.cap is None or not self.cap.isOpened():
                self._try_open_stream()
                time.sleep(0.2)
                continue

            ret, frame = self.cap.read()
            if ret:
                self.ret = True
                self.frame = frame
                continue

            self.ret = False
            self._release_capture()
            time.sleep(0.5)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self.update, daemon=True)
        self._thread.start()

    def stop(self):
        self.stopped = True
        self._release_capture()


class TelegramAlertService:

    def __init__(self, token: str, chat_id: str, cooldown: float = 10):
        self.bot = telepot.Bot(token)
        self.chat_id = chat_id
        self.cooldown = cooldown
        self.last_alert = 0.0

    def can_send(self, now: float) -> bool:
        return now - self.last_alert >= self.cooldown

    def _send_photo_worker(self, camera_name: str, alert_frame):
        try:
            ok, buffer = cv2.imencode(".jpg", alert_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if not ok:
                raise RuntimeError("Could not encode alert frame")

            photo = io.BytesIO(buffer.tobytes())
            photo.name = f"alert_{camera_name}.jpg"
            self.bot.sendPhoto(
                self.chat_id,
                photo,
                caption=f"Intruder detected on {camera_name}",
            )
            print(f"[{camera_name}] Photo sent to Telegram.")
        except Exception as exc:
            print(f"Telegram error: {exc}")

    def send_async(self, camera_name: str, alert_frame, now: float):
        if not self.can_send(now):
            return
        self.last_alert = now
        threading.Thread(
            target=self._send_photo_worker,
            args=(camera_name, alert_frame),
            daemon=True,
        ).start()


class NullTelegramAlertService:

    def __init__(self):
        self.cooldown = 0
        self.last_alert = 0.0

    def send_async(self, camera_name: str, alert_frame, now: float):
        return


class DetectionService:

    def __init__(
        self,
        skip_frames: int = 1,
        ia_interval: float = 0.1,
        face_model_path: str = str(FACE_MODEL_FILE),
        pose_model_path: str = str(POSE_MODEL_FILE),
        min_face_confidence: float = 0.5,
        min_face_size: int = 40,
        history_size: int = 5,
        min_positive_frames: int = 1,
    ):
        self.skip_frames = skip_frames
        self.ia_interval = ia_interval
        self.frame_count = 0
        self.last_ia_time = 0.0
        self.min_face_confidence = min_face_confidence
        self.min_face_size = min_face_size
        self.history = deque(maxlen=history_size)
        self.min_positive_frames = min_positive_frames
        self.last_active_detection = False

        base_options_face = python.BaseOptions(model_asset_path=face_model_path)
        options_face = vision.FaceDetectorOptions(
            base_options=base_options_face,
            min_detection_confidence=min_face_confidence,
            min_suppression_threshold=0.5,
        )
        self.face_detector = vision.FaceDetector.create_from_options(options_face)

        base_options_pose = python.BaseOptions(model_asset_path=pose_model_path)
        options_pose = vision.PoseLandmarkerOptions(
            base_options=base_options_pose,
            num_poses=1,
            min_pose_detection_confidence=0.6,
            min_pose_presence_confidence=0.6,
            min_tracking_confidence=0.6,
        )
        self.pose_detector = vision.PoseLandmarker.create_from_options(options_pose)

    def _is_face_valid(self, bbox, frame_width: int, frame_height: int) -> bool:
        x = bbox.origin_x
        y = bbox.origin_y
        w = bbox.width
        h = bbox.height

        if w < self.min_face_size or h < self.min_face_size:
            return False

        if x <= 5 or y <= 5:
            return False

        if x + w >= frame_width - 5 or y + h >= frame_height - 5:
            return False

        aspect_ratio = w / float(h)
        if aspect_ratio < 0.6 or aspect_ratio > 1.6:
            return False

        return w * h >= 1600

    def _get_valid_faces(self, face_result, frame):
        frame_height, frame_width = frame.shape[:2]
        valid_boxes = []

        for det in face_result.detections:
            score = det.categories[0].score if det.categories else 0.0
            bbox = det.bounding_box

            if score < self.min_face_confidence:
                continue

            if not self._is_face_valid(bbox, frame_width, frame_height):
                continue

            valid_boxes.append((bbox, score))

        return valid_boxes

    def _has_supporting_pose(self, pose_result) -> bool:
        if not pose_result.pose_landmarks:
            return False

        landmarks = pose_result.pose_landmarks[0]
        visible = 0

        for lm in landmarks:
            if 0.0 <= lm.x <= 1.0 and 0.0 <= lm.y <= 1.0:
                visible += 1

        return visible >= 8

    def _is_persistent_detection(self) -> bool:
        return sum(self.history) >= self.min_positive_frames

    def annotate(self, frame):
        """Annotates a frame and reports whether anything relevant was detected.

        Returns:
            A tuple ``(annotated_frame, active_detection)``.
        """
        frame = cv2.resize(frame, (640, 480))
        self.frame_count += 1

        if self.frame_count % self.skip_frames != 0:
            return frame, self.last_active_detection

        now = time.time()
        if now - self.last_ia_time < self.ia_interval:
            return frame, self.last_active_detection

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
        )
        face_result = self.face_detector.detect(mp_image)
        valid_faces = self._get_valid_faces(face_result, frame)

        pose_result = self.pose_detector.detect(mp_image)
        pose_support = self._has_supporting_pose(pose_result)

        current_detection = len(valid_faces) > 0 or pose_support
        self.history.append(current_detection)
        active_detection = self._is_persistent_detection()
        self.last_active_detection = active_detection

        for bbox, score in valid_faces:
            cv2.rectangle(
                frame,
                (bbox.origin_x, bbox.origin_y),
                (bbox.origin_x + bbox.width, bbox.origin_y + bbox.height),
                (255, 0, 0),
                2,
            )
            cv2.putText(
                frame,
                f"Face {score:.2f}",
                (bbox.origin_x, max(20, bbox.origin_y - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 0, 0),
                1,
            )

        if pose_support:
            landmark = pose_result.pose_landmarks[0][0]
            cx, cy = int(landmark.x * 640), int(landmark.y * 480)
            cv2.circle(frame, (cx, cy), 10, (0, 255, 0), -1)

        cv2.putText(
            frame,
            f"Presence: {'ON' if active_detection else 'OFF'}",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0) if active_detection else (0, 0, 255),
            2,
        )

        self.last_ia_time = now
        return frame, active_detection


class TapoController:

    def __init__(
        self,
        camera_name: str,
        camera_type: str,
        stream_url: str,
        tapo_user: Optional[str] = None,
        tapo_pass: Optional[str] = None,
        max_tilt: int = 114,
        retry_interval: int = 10,
    ):
        self.camera_name = camera_name
        self.camera_type = str(camera_type).lower()
        self.max_tilt = max_tilt
        self.retry_interval = retry_interval
        self.tapo_client = None
        self.connecting = False
        self.last_try = 0.0

        self.tapo_user = tapo_user or os.getenv("TAPO_USER")
        self.tapo_pass = tapo_pass or os.getenv("TAPO_PASS")
        self.ip = self._extract_ip(stream_url)

        if self.camera_type != "tapo":
            print(f"[{self.camera_name}] Camera type '{camera_type}' without PTZ.")
        elif not self.tapo_user or not self.tapo_pass:
            print(f"[{self.camera_name}] Missing Tapo credentials; PTZ disabled.")
        elif self.ip:
            print(f"[{self.camera_name}] Tapo PTZ will connect on demand.")
        else:
            print(f"[{self.camera_name}] No Tapo IP found in URL; PTZ disabled.")

    @staticmethod
    def _extract_ip(url: str) -> Optional[str]:
        ip_match = re.search(r"@([\d\.]+):", url)
        return ip_match.group(1) if ip_match else None

    @property
    def enabled(self) -> bool:
        return self.camera_type == "tapo" and bool(self.ip)

    def _connect_worker(self):
        try:
            self.tapo_client = Tapo(self.ip, self.tapo_user, self.tapo_pass)
            print(f"[{self.camera_name}] Motion control linked.")
        except Exception as exc:
            self.tapo_client = None
            print(f"[{self.camera_name}] Could not connect to PTZ motor: {exc}")
        finally:
            self.connecting = False

    def ensure_connected(self) -> bool:
        if not self.enabled:
            return False
        if self.tapo_client:
            return True
        if self.connecting:
            return False
        now = time.time()
        if now - self.last_try < self.retry_interval:
            return False

        self.last_try = now
        self.connecting = True
        threading.Thread(target=self._connect_worker, daemon=True).start()
        return False

    def move(self, x: int, y: int):
        if self.camera_type != "tapo":
            return
        if not self.tapo_client:
            self.ensure_connected()
            return

        try:
            safe_y = max(min(y, self.max_tilt), -self.max_tilt)
            threading.Thread(
                target=self.tapo_client.moveMotor,
                args=(x, safe_y),
                daemon=True,
            ).start()
            print(f"[{self.camera_name}] Touch movement: {x}, {safe_y}")
            if safe_y != y:
                print(f"[{self.camera_name}] Warning: tilt limited to {safe_y} degrees.")
        except Exception as exc:
            print(f"Motor error: {exc}")

    def is_online(self) -> bool:
        if not self.enabled:
            return False
        try:
            with socket.create_connection((self.ip, 554), timeout=1.0):
                return True
        except Exception:
            return False


class Esp32LightController:
    """Controls the flashlight LED exposed by the common ESP32-CAM webserver."""

    def __init__(
        self,
        camera_name: str,
        camera_type: str,
        stream_url: str,
        request_timeout: float = 2.0,
        flash_on_value: int = 12,
    ):
        self.camera_name = camera_name
        self.camera_type = str(camera_type).lower()
        self.request_timeout = request_timeout
        self.flash_on_value = flash_on_value
        self.is_on = False
        self._parsed_url = urlparse(stream_url)

    @property
    def enabled(self) -> bool:
        return self.camera_type == "esp32" and bool(self._parsed_url.hostname)

    def _control_urls(self) -> list[str]:
        if not self.enabled:
            return []

        scheme = self._parsed_url.scheme or "http"
        host = self._parsed_url.hostname
        stream_port = self._parsed_url.port

        urls = [f"{scheme}://{host}/control"]
        if stream_port and stream_port != 80:
            urls.append(f"{scheme}://{host}:{stream_port}/control")
        return urls

    def set_light(self, enabled: bool) -> bool:
        if not self.enabled:
            return False

        value = self.flash_on_value if enabled else 0
        last_error = None

        for control_url in self._control_urls():
            try:
                response = requests.get(
                    control_url,
                    params={"var": "led_intensity", "val": value},
                    timeout=self.request_timeout,
                )
                if response.ok:
                    self.is_on = enabled
                    return True
            except requests.RequestException as exc:
                last_error = exc

        if last_error:
            print(f"[{self.camera_name}] Could not change ESP32 light state: {last_error}")
        return False

    def toggle(self) -> bool:
        return self.set_light(not self.is_on)


class CameraHealthMonitor:
    """Keeps track of the observable health state of a camera."""

    def __init__(self, camera_name: str, camera_type: str, health_interval: int = 10):
        self.camera_name = camera_name
        self.camera_type = str(camera_type).lower()
        self.health_interval = health_interval
        self.last_health_check = 0.0
        self.stream_online = False
        self.ptz_online = False
        self.last_stream_state = None
        self.last_ptz_state = None

    def refresh(self, stream_online: bool, ptz_online: bool):
        now = time.time()
        if now - self.last_health_check < self.health_interval:
            return

        self.last_health_check = now
        self.stream_online = stream_online
        self.ptz_online = ptz_online

    def get_state_changes(self):
        messages = []

        if self.last_stream_state is None:
            self.last_stream_state = self.stream_online
        elif self.stream_online != self.last_stream_state:
            state = "ONLINE" if self.stream_online else "OFFLINE"
            messages.append(f"[{self.camera_name}] STREAM {state}")
            self.last_stream_state = self.stream_online

        if self.camera_type == "tapo":
            if self.last_ptz_state is None:
                self.last_ptz_state = self.ptz_online
            elif self.ptz_online != self.last_ptz_state:
                state = "ONLINE" if self.ptz_online else "OFFLINE"
                messages.append(f"[{self.camera_name}] PTZ {state}")
                self.last_ptz_state = self.ptz_online

        return messages


class GestionCamara:
    """Public facade for a system camera.

    It preserves the contract used by the rest of the project while delegating
    each responsibility to a specialized collaborator.
    """

    def __init__(
        self,
        nombre,
        url,
        token_tg,
        chat_id_tg,
        tipo="Tapo",
        tapo_user=None,
        tapo_pass=None,
        alert_cooldown: float = 10,
    ):
        self.nombre = nombre
        self.url = url
        self.tipo = tipo
        self.alarm_enabled = True
        self.last_status_message = 0
        self.status_cooldown = 60

        self.stream_reader = StreamReader(url)
        if token_tg and chat_id_tg:
            self.alert_service = TelegramAlertService(token_tg, chat_id_tg, cooldown=alert_cooldown)
        else:
            self.alert_service = NullTelegramAlertService()
        self.detection_service = DetectionService()
        self.ptz_controller = TapoController(
            camera_name=nombre,
            camera_type=tipo,
            stream_url=url,
            tapo_user=tapo_user,
            tapo_pass=tapo_pass,
        )
        self.light_controller = Esp32LightController(
            camera_name=nombre,
            camera_type=tipo,
            stream_url=url,
        )
        self.health_monitor = CameraHealthMonitor(camera_name=nombre, camera_type=tipo)

    @property
    def cap(self):
        return self.stream_reader.cap

    @property
    def ret(self):
        return self.stream_reader.ret

    @property
    def frame(self):
        return self.stream_reader.frame

    @property
    def stopped(self):
        return self.stream_reader.stopped

    @property
    def stream_online(self):
        return self.health_monitor.stream_online

    @property
    def ptz_online(self):
        return self.health_monitor.ptz_online

    @property
    def last_stream_state(self):
        return self.health_monitor.last_stream_state

    @last_stream_state.setter
    def last_stream_state(self, value):
        self.health_monitor.last_stream_state = value

    @property
    def last_ptz_state(self):
        return self.health_monitor.last_ptz_state

    @last_ptz_state.setter
    def last_ptz_state(self, value):
        self.health_monitor.last_ptz_state = value

    @property
    def last_health_check(self):
        return self.health_monitor.last_health_check

    @property
    def cooldown(self):
        return self.alert_service.cooldown

    @property
    def last_alert(self):
        return self.alert_service.last_alert

    @property
    def light_enabled(self):
        return self.light_controller.enabled

    @property
    def light_is_on(self):
        return self.light_controller.is_on

    def move(self, x, y):
        self.ptz_controller.move(x, y)

    def set_light(self, enabled: bool):
        return self.light_controller.set_light(enabled)

    def toggle_light(self):
        return self.light_controller.toggle()

    def start(self):
        self.stream_reader.start()
        return self

    def update(self):
        """Kept for compatibility with the previous update-based API."""
        self.stream_reader.update()

    def send_telegram_alert(self, alert_frame):
        self.alert_service.send_async(self.nombre, alert_frame, time.time())

    def get_processed_frame(self, send_alerts: bool = True):
        """Processes the latest frame and returns the annotated version.

        If the alarm is enabled and a presence is detected, it triggers an
        asynchronous Telegram alert while respecting the configured cooldown.
        """
        if not self.ret or self.frame is None:
            return None

        frame, active_detection = self.detection_service.annotate(self.frame)
        now = time.time()
        if send_alerts and self.alarm_enabled and active_detection:
            self.alert_service.send_async(self.nombre, frame.copy(), now)

        cv2.putText(frame, self.nombre, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        return frame

    def process_frame(self):
        return self.get_processed_frame(send_alerts=True)

    def check_health(self):
        stream_online = bool(self.ret and self.frame is not None)
        ptz_online = self.ptz_controller.is_online()
        self.health_monitor.refresh(stream_online=stream_online, ptz_online=ptz_online)

    def get_state_changes(self):
        return self.health_monitor.get_state_changes()

    def stop(self):
        self.stream_reader.stop()
