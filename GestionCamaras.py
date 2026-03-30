import cv2
import os
import threading
import telepot
import time
import socket
from urllib.parse import urlparse
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from pytapo import Tapo

class GestionCamara:
    def __init__(self, nombre, url, token_tg, chat_id_tg, tipo="Tapo", tapo_user=None, tapo_pass=None):
        self.nombre = nombre
        self.url = url
        self.tipo = tipo
        self.cap = None
        self.ret = False
        self.frame = None
        self.stopped = False
        self.frame_count = 0
        self.skip_frames = 4 # Skip 4 frames to reduce CPU usage.
        self.alarm_enabled = True # By default, the alarm is enabled.
        
        # Check to the status cam, actived or desacted.
        '''
            The reason is so thtat you don't wait to connect to cameras that are turned off by reasons
            outside the program, a camera unplugged or without battery, hardware failures...
        '''
        self.stream_online = False
        self.ptz_online = False
        self.last_stream_state = None
        self.last_ptz_state = None
        self.last_health_check = 0

        # Control de reintentos / spam
        self.health_interval = 10 # seconds
        self.last_status_message = 0
        self.status_cooldown = 60 # Do not repeat the same notification too frequently.
               
        # Telegram configuration
        self.bot = telepot.Bot(token_tg)
        self.chat_id = chat_id_tg
        self.last_alert = 0 # Timestamp of the last alert to avoid spamming.
        self.cooldown = 60 # Number of seconds to wait between photos.

        self.tapo_client = None
        self.ip = None
        self.Max_tilt_tapo = 114
        self.Max_pan_tapo = 360
        self.ia_interval = 0.3
        self.last_ia_time = 0
        self.last_tapo_try = 0
        self.tapo_retry_interval = 10
        self.tapo_connecting = False
        self.last_stream_open_try = 0
        self.stream_open_interval = 3

        parsed_stream = urlparse(self.url)
        self.stream_host = parsed_stream.hostname
        if parsed_stream.port:
            self.stream_port = parsed_stream.port
        elif parsed_stream.scheme == "rtsp":
            self.stream_port = 554
        elif parsed_stream.scheme == "http":
            self.stream_port = 80
        else:
            self.stream_port = None

        # PTZ (Tapo) is optional: ESP32 or other cameras can be used without it.
        if str(self.tipo).lower() == "tapo":
            self.tapo_user = tapo_user or os.getenv("TAPO_USER")
            self.tapo_pass = tapo_pass or os.getenv("TAPO_PASS")

            # Automatically extract the IP address from the RTSP URL.
            import re
            ip_match = re.search(r'@([\d\.]+):', url)
            self.ip = ip_match.group(1) if ip_match else None

            if not self.tapo_user or not self.tapo_pass:
                print(f"[{self.nombre}] Tapo credentials missing; PTZ disabled.")
            elif self.ip:
                print(f"[{self.nombre}] Tapo PTZ will connect on demand.")
            else:
                print(f"[{self.nombre}] No Tapo IP found in URL; PTZ disabled.")
        else:
            print(f"[{self.nombre}] Camera type '{self.tipo}' without PTZ.")

        # --- FACE DETECTION (MediaPipe) ---
        base_options_face = python.BaseOptions(model_asset_path='face_detector.task')
        options_face = vision.FaceDetectorOptions(base_options=base_options_face)
        self.face_detector = vision.FaceDetector.create_from_options(options_face)

        # --- POSE DETECTION (MediaPipe) ---
        base_options_pose = python.BaseOptions(model_asset_path='pose_landmarker.task')
        options_pose = vision.PoseLandmarkerOptions(base_options=base_options_pose)
        self.pose_detector = vision.PoseLandmarker.create_from_options(options_pose)

    def _quick_tcp_check(self, host, port, timeout=1.0):
        """Fast non-blocking reachability check for camera services."""
        if not host or not port:
            return False
        try:
            with socket.create_connection((host, int(port)), timeout=timeout):
                return True
        except Exception:
            return False

    def _try_open_stream(self):
        """Open stream only if host is reachable to avoid long blocking retries."""
        now = time.time()
        if now - self.last_stream_open_try < self.stream_open_interval:
            return
        self.last_stream_open_try = now

        if not self._quick_tcp_check(self.stream_host, self.stream_port, timeout=0.8):
            self.ret = False
            return

        self.cap = cv2.VideoCapture(self.url)

    def _connect_tapo_worker(self):
        try:
            self.tapo_client = Tapo(self.ip, self.tapo_user, self.tapo_pass)
            self.ptz_online = True
            print(f"[{self.nombre}] Control de movimiento vinculado.")
        except Exception as e:
            self.tapo_client = None
            self.ptz_online = False
            print(f"[{self.nombre}] No se pudo conectar al motor: {e}")
        finally:
            self.tapo_connecting = False

    def _ensure_tapo_connected(self):
        """Trigger non-blocking reconnection attempts for PTZ."""
        if str(self.tipo).lower() != "tapo" or not self.ip:
            return False
        if self.tapo_client:
            return True
        if self.tapo_connecting:
            return False
        now = time.time()
        if now - self.last_tapo_try < self.tapo_retry_interval:
            return False
        self.last_tapo_try = now
        self.tapo_connecting = True
        threading.Thread(target=self._connect_tapo_worker, daemon=True).start()
        return False

    def check_health(self):
        """Refresh camera health state without blocking the main loop."""
        now = time.time()
        if now - self.last_health_check < self.health_interval:
            return

        self.last_health_check = now

        # Stream health: if frames are being updated, stream is considered online.
        self.stream_online = bool(self.ret and self.frame is not None)

        # PTZ health (Tapo only): keep it lightweight using TCP reachability.
        if str(self.tipo).lower() == "tapo" and self.ip:
            self.ptz_online = self._quick_tcp_check(self.ip, 554, timeout=1.0)
        else:
            self.ptz_online = False

    def get_state_changes(self):
        """Return status messages only when a state change is detected."""
        messages = []

        if self.last_stream_state is None:
            self.last_stream_state = self.stream_online
        elif self.stream_online != self.last_stream_state:
            state = "ONLINE" if self.stream_online else "OFFLINE"
            messages.append(f"[{self.nombre}] STREAM {state}")
            self.last_stream_state = self.stream_online

        if str(self.tipo).lower() == "tapo":
            if self.last_ptz_state is None:
                self.last_ptz_state = self.ptz_online
            elif self.ptz_online != self.last_ptz_state:
                state = "ONLINE" if self.ptz_online else "OFFLINE"
                messages.append(f"[{self.nombre}] PTZ {state}")
                self.last_ptz_state = self.ptz_online

        return messages

    def move(self, x, y):
        """ move the cam based on the user's swipe, limiting tilt to 114 degrees """
        if str(self.tipo).lower() == "tapo" and self.tapo_client:
            try:
                # Prevent the tilt value (y) from exceeding the physical limits of the Tapo camera.
                max_tilt = self.Max_tilt_tapo if hasattr(self, 'Max_tilt_tapo') else 114
                min_tilt = -self.Max_tilt_tapo if hasattr(self, 'Max_tilt_tapo') else -114

                # Limit y within the allowed ranges
                safe_y = max(min(y, max_tilt), min_tilt)

                # Launch the movement using the corrected tilt
                threading.Thread(target=self.tapo_client.moveMotor, args=(x, safe_y), daemon=True).start()
                print(f"[{self.nombre}] Touch movement: {x}, {safe_y}")
                if safe_y != y:
                    print(f"[{self.nombre}] Warning: Tilt limited to {safe_y} degrees to avoid exceeding the maximum allowed.")
            except Exception as e:
                print(f"Motor error: {e}")
        elif str(self.tipo).lower() == "tapo":
            self._ensure_tapo_connected()
           
    def start(self):
        # The thread calls self.update.
        threading.Thread(target=self.update, daemon=True).start()
        return self

    def update(self):
        while not self.stopped:
            if self.cap is None or not self.cap.isOpened():
                self._try_open_stream()
                time.sleep(0.2)
                continue

            ret, frame = self.cap.read()
            if ret:
                self.ret, self.frame = True, frame
            else:
                self.ret = False
                if self.cap:
                    self.cap.release()
                self.cap = None
                time.sleep(0.5)

    def send_telegram_alert(self, alert_frame):
        """Internal function to send the latest frame in a separate thread."""
        try:
            file_name = f"alerta_{self.nombre}.jpg"
            cv2.imwrite(file_name, alert_frame)
            with open(file_name, 'rb') as f:
                self.bot.sendPhoto(self.chat_id, f, caption= f"⚠️ ¡Intruso detectado en {self.nombre}!")
            print(f"[{self.nombre}] Photo sent to Telegram.")
            os.remove(file_name) # Clean temporary file.
        except Exception as e:
            print(f"Error Telegram: {e}")
    
    def process_frame(self):
        if not self.ret or self.frame is None: return None
        
        frame = cv2.resize(self.frame, (640, 480))
        self.frame_count +=1
        active_detection = False

        # Frame skip logic to reduce processing load.
        if self.frame_count % self.skip_frames == 0:
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

            now = time.time()
            if now - self.last_ia_time >= self.ia_interval:
                # 1. FACE DETECTION (MediaPipe)
                face_result = self.face_detector.detect(mp_image)
                if face_result.detections:
                    active_detection = True
                    for det in face_result.detections:
                        bbox = det.bounding_box
                        cv2.rectangle(frame, (bbox.origin_x, bbox.origin_y), 
                                    (bbox.origin_x + bbox.width, bbox.origin_y + bbox.height), (255, 0, 0), 2)

                # 2. POSE DETECTION (MediaPipe)
                pose_result = self.pose_detector.detect(mp_image)
                if pose_result.pose_landmarks:
                    active_detection = True
                    # Only draw a reference point (e.g., nose or shoulder).
                    landmark = pose_result.pose_landmarks[0][0] # Nose landmark.
                    cx, cy = int(landmark.x * 640), int(landmark.y * 480)
                    cv2.circle(frame, (cx, cy), 10, (0, 255, 0), -1)

                # Only send to Telegram if the alarm is enabled.
                if self.alarm_enabled and active_detection and (now - self.last_alert > self.cooldown):
                    self.last_alert = now
                    threading.Thread(target=self.send_telegram_alert, args=(frame.copy(),), daemon=True).start()
                
                self.last_ia_time = now

        cv2.putText(frame, self.nombre, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        return frame
    
    def stop(self):
        self.stopped = True
        self.cap.release()
