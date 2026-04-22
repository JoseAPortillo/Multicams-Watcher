import math
import time

import cv2
import numpy as np

from app.core.constants import FRAME_SIZE


class SimulatedPTZController:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled


class SimulatedCamera:
    def __init__(self, camera_id: int, name: str, camera_type: str = "Simulated", ptz_enabled: bool = True):
        self.camera_id = camera_id
        self.nombre = name
        self.tipo = camera_type
        self.alarm_enabled = True
        self.last_status_message = 0
        self.status_cooldown = 60
        self.ret = True
        self.frame = None
        self._running = False
        self._phase = camera_id * 0.8
        self._ptz_x = 0
        self._ptz_y = 0
        self._light_on = False
        self.ptz_controller = SimulatedPTZController(enabled=ptz_enabled)
        self._health_messages = []
        self._stream_online = True

    def start(self):
        self._running = True
        return self

    def stop(self):
        self._running = False

    def move(self, x, y):
        if not self.ptz_controller.enabled:
            return
        self._ptz_x = max(min(self._ptz_x + x, 90), -90)
        self._ptz_y = max(min(self._ptz_y + y, 90), -90)

    @property
    def light_enabled(self):
        return self.tipo.lower() == "esp32"

    @property
    def light_is_on(self):
        return self._light_on

    def set_light(self, enabled: bool):
        if not self.light_enabled:
            return False
        self._light_on = bool(enabled)
        return True

    def toggle_light(self):
        return self.set_light(not self._light_on)

    def _build_frame(self):
        width, height = FRAME_SIZE
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        now = time.time()
        wave = math.sin(now * 1.2 + self._phase)
        pulse = math.cos(now * 0.8 + self._phase)

        frame[:, :] = (24, 20, 16)
        cv2.rectangle(frame, (0, 0), (width, 84), (28, 86, 74), -1)
        cv2.putText(frame, self.nombre, (22, 42), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (240, 240, 240), 2)
        cv2.putText(frame, f"Type: {self.tipo}", (22, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (220, 220, 220), 2)

        cx = int(width * (0.5 + 0.28 * wave))
        cy = int(height * (0.55 + 0.18 * pulse))
        color = (70, 170, 255) if self.alarm_enabled else (120, 120, 120)
        cv2.circle(frame, (cx, cy), 52, color, -1)
        cv2.rectangle(frame, (cx - 28, cy - 72), (cx + 28, cy + 72), (80, 220, 120), 3)

        cv2.putText(
            frame,
            f"Alarm: {'ON' if self.alarm_enabled else 'OFF'}",
            (22, height - 54),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (90, 220, 140) if self.alarm_enabled else (180, 180, 180),
            2,
        )
        cv2.putText(
            frame,
            f"PTZ: {self._ptz_x:+d}, {self._ptz_y:+d}",
            (22, height - 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (230, 230, 230),
            2,
        )
        cv2.putText(
            frame,
            f"Light: {'ON' if self.light_is_on else 'OFF'}",
            (22, height - 84),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 225, 120) if self.light_is_on else (180, 180, 180),
            2,
        )
        cv2.putText(
            frame,
            time.strftime("%Y-%m-%d %H:%M:%S"),
            (width - 250, height - 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (180, 180, 180),
            2,
        )

        if self.ptz_controller.enabled:
            center_x, center_y = width - 80, 120
            cv2.circle(frame, (center_x, center_y), 44, (80, 80, 80), 2)
            marker_x = int(center_x + (self._ptz_x / 90.0) * 28)
            marker_y = int(center_y - (self._ptz_y / 90.0) * 28)
            cv2.circle(frame, (marker_x, marker_y), 10, (255, 255, 255), -1)

        self.frame = frame
        return frame

    def get_processed_frame(self, send_alerts: bool = True):
        if not self._running:
            return None
        return self._build_frame()

    def process_frame(self):
        return self.get_processed_frame(send_alerts=False)

    def check_health(self):
        if not self._running:
            return
        self._stream_online = True

    def get_state_changes(self):
        messages = self._health_messages[:]
        self._health_messages.clear()
        return messages


def build_simulated_streams(count: int = 3):
    streams = []
    for idx in range(count):
        ptz_enabled = idx == 0
        camera = SimulatedCamera(
            camera_id=idx,
            name=f"SimCam {idx + 1}",
            camera_type="ESP32" if idx > 0 else "Simulated",
            ptz_enabled=ptz_enabled,
        )
        streams.append(camera.start())
    return streams
