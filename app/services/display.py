"""
Display and UI rendering for multi-camera monitoring.
Handles mosaic view, fullscreen, and touch interactions.
"""
import math

import cv2
import numpy as np

from app.core.constants import ALTO_PI, ANCHO_PI, FRAME_SIZE


BLACK_FRAME = np.zeros((FRAME_SIZE[1], FRAME_SIZE[0], 3), np.uint8)
LIGHT_BUTTON_RECT = (ANCHO_PI - 180, 16, ANCHO_PI - 20, 64)


def safe_frame(frame):
    """Return frame or black placeholder if None."""
    return frame if frame is not None else BLACK_FRAME.copy()


def build_offline_tile(camera, width: int, height: int) -> np.ndarray:
    """Build offline/unavailable camera tile."""
    tile = np.zeros((height, width, 3), np.uint8)
    cv2.putText(tile, camera.nombre, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
    cv2.putText(tile, "OFFLINE", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
    return tile


def point_in_rect(x: int, y: int, rect: tuple[int, int, int, int]) -> bool:
    """Return True when a point is inside a rectangle."""
    left, top, right, bottom = rect
    return left <= x <= right and top <= y <= bottom


def draw_light_button(canvas: np.ndarray, camera) -> None:
    """Draw the ESP32 light toggle button on fullscreen view."""
    if not getattr(camera, "light_enabled", False):
        return

    left, top, right, bottom = LIGHT_BUTTON_RECT
    is_on = getattr(camera, "light_is_on", False)
    bg_color = (70, 170, 255) if is_on else (70, 70, 70)
    border_color = (210, 240, 255) if is_on else (180, 180, 180)
    label = "LUZ ON" if is_on else "LUZ OFF"

    cv2.rectangle(canvas, (left, top), (right, bottom), bg_color, -1)
    cv2.rectangle(canvas, (left, top), (right, bottom), border_color, 2)
    cv2.putText(canvas, label, (left + 20, top + 32), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)


def render_fullscreen(camera) -> np.ndarray:
    """Render single camera fullscreen with labels."""
    frame = camera.process_frame()
    if frame is None:
        canvas = build_offline_tile(camera, ANCHO_PI, ALTO_PI)
    else:
        canvas = cv2.resize(frame, (ANCHO_PI, ALTO_PI))
    cv2.putText(canvas, f"CONTROL: {camera.nombre}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    draw_light_button(canvas, camera)
    return canvas


def render_mosaic(cameras: list) -> np.ndarray:
    """Render all cameras as mosaic grid."""
    if not cameras:
        return np.zeros((ALTO_PI, ANCHO_PI, 3), np.uint8)

    total_cameras = len(cameras)
    cols = math.ceil(math.sqrt(total_cameras))
    rows = math.ceil(total_cameras / cols)

    tile_width = ANCHO_PI // cols
    tile_height = ALTO_PI // rows
    tiles = []

    for camera in cameras:
        frame = camera.process_frame()
        if frame is None:
            tile = build_offline_tile(camera, tile_width, tile_height)
        else:
            tile = cv2.resize(frame, (tile_width, tile_height))
        tiles.append(tile)

    total_cells = rows * cols
    while len(tiles) < total_cells:
        tiles.append(np.zeros((tile_height, tile_width, 3), np.uint8))

    row_images = []
    for row_index in range(rows):
        start = row_index * cols
        end = start + cols
        row_images.append(np.hstack(tiles[start:end]))

    return np.vstack(row_images)


def camera_index_from_mosaic_point(x: int, y: int, cameras: list) -> int | None:
    """Get camera index from mosaic touch point."""
    if not cameras:
        return None

    total_cameras = len(cameras)
    cols = math.ceil(math.sqrt(total_cameras))
    rows = math.ceil(total_cameras / cols)
    tile_width = ANCHO_PI // cols
    tile_height = ALTO_PI // rows

    if tile_width <= 0 or tile_height <= 0:
        return None

    col = x // tile_width
    row = y // tile_height
    idx = row * cols + col
    return idx if 0 <= idx < total_cameras else None


class TouchManager:
    """Manages touch events for camera UI."""

    def __init__(self, max_camera=None, init_point_touch=None):
        self.max_camera = max_camera
        self.init_point_touch = init_point_touch
        self.pending_light_toggle = False

    def handle_double_click(self, x: int, y: int, streams: list):
        """Toggle between mosaic and fullscreen."""
        if self.max_camera is None:
            idx = camera_index_from_mosaic_point(x, y, streams)
            if idx is not None:
                self.max_camera = streams[idx]
                print(f"Maximizando: {self.max_camera.nombre}")
            return

        self.max_camera = None
        print("Volviendo al mosaico")

    def handle_light_button(self, event: int, x: int, y: int) -> bool:
        """Handle clicks on the ESP32 light button."""
        if self.max_camera is None or not getattr(self.max_camera, "light_enabled", False):
            return False

        over_button = point_in_rect(x, y, LIGHT_BUTTON_RECT)

        if event == cv2.EVENT_LBUTTONDBLCLK and over_button:
            return True

        if event == cv2.EVENT_LBUTTONDOWN and over_button:
            self.pending_light_toggle = True
            self.init_point_touch = None
            return True

        if event == cv2.EVENT_LBUTTONUP and self.pending_light_toggle:
            self.pending_light_toggle = False
            if over_button:
                self.max_camera.toggle_light()
                state = "encendida" if getattr(self.max_camera, "light_is_on", False) else "apagada"
                print(f"[{self.max_camera.nombre}] Luz {state}")
            return True

        return False

    def handle_swipe(self, event: int, x: int, y: int):
        """Handle swipe/pan gesture for PTZ control."""
        if not self.max_camera:
            return

        if event == cv2.EVENT_LBUTTONDOWN:
            self.init_point_touch = (x, y)
            return

        if event != cv2.EVENT_LBUTTONUP or self.init_point_touch is None:
            return

        dx = x - self.init_point_touch[0]
        dy = y - self.init_point_touch[1]
        self.init_point_touch = None

        if abs(dx) <= 40 and abs(dy) <= 40:
            return

        mov_x = 15 if dx > 40 else -15 if dx < -40 else 0
        mov_y = 15 if dy < -40 else -15 if dy > 40 else 0
        self.max_camera.move(mov_x, mov_y)

    def touch_callback(self, event: int, x: int, y: int, flags: int, param: dict):
        """OpenCV mouse callback for touch events."""
        if self.handle_light_button(event, x, y):
            return

        if event == cv2.EVENT_LBUTTONDBLCLK:
            self.handle_double_click(x, y, param["streams"])
            return

        self.handle_swipe(event, x, y)
