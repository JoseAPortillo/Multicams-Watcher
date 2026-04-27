import atexit
import os
from contextlib import asynccontextmanager
from pathlib import Path

import cv2
import telepot
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.cameras import health_monitor
from app.core.settings import WEBAPP_DIR
from app.services.video_watcher import bootstrap_system


DEV_DISABLE_TELEGRAM = os.getenv("CONTROL_APP_DISABLE_TELEGRAM", "").lower() in {"1", "true", "yes", "on"}
DEV_DISABLE_HEALTH_MONITOR = os.getenv("CONTROL_APP_DISABLE_HEALTH_MONITOR", "").lower() in {"1", "true", "yes", "on"}
SIMULATION_MODE = os.getenv("CONTROL_APP_SIMULATE", "").lower() in {"1", "true", "yes", "on"}
SIMULATED_CAMERA_COUNT = int(os.getenv("CONTROL_APP_SIM_CAMERA_COUNT", "3"))

env_vars, streams = bootstrap_system(
    require_telegram=not DEV_DISABLE_TELEGRAM,
    simulate=SIMULATION_MODE,
    simulated_count=SIMULATED_CAMERA_COUNT,
)
bot = telepot.Bot(env_vars["TOKEN_TG"]) if not DEV_DISABLE_TELEGRAM else None
_health_thread_started = False


def get_camera(camera_id: int):
    if camera_id < 0 or camera_id >= len(streams):
        raise HTTPException(status_code=404, detail="Camera not found")
    return streams[camera_id]


def ensure_started():
    global _health_thread_started
    for stream in streams:
        stream.start()

    if not DEV_DISABLE_HEALTH_MONITOR and not DEV_DISABLE_TELEGRAM and not _health_thread_started:
        health_monitor.start_health_monitor_thread(streams, bot, env_vars["CHAT_ID_TG"])
        _health_thread_started = True


def shutdown_streams():
    for stream in streams:
        stream.stop()


atexit.register(shutdown_streams)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_started()
    yield
    shutdown_streams()


app = FastAPI(title="Multicams-Watcher", lifespan=lifespan)
app.mount("/app", StaticFiles(directory=str(WEBAPP_DIR), html=True), name="webapp")


@app.get("/")
def root():
    return RedirectResponse(url="/app")


@app.get("/api/health")
def health():
    online = sum(1 for cam in streams if cam.ret and cam.frame is not None)
    return {
        "status": "ok",
        "cameras_total": len(streams),
        "cameras_online": online,
        "telegram_enabled": not DEV_DISABLE_TELEGRAM,
        "health_monitor_enabled": not DEV_DISABLE_HEALTH_MONITOR and not DEV_DISABLE_TELEGRAM,
        "simulation_mode": SIMULATION_MODE,
    }


@app.get("/api/cameras")
def list_cameras():
    return [
        {
            "id": idx,
            "name": cam.nombre,
            "type": cam.tipo,
            "online": bool(cam.ret and cam.frame is not None),
            "alarm_enabled": cam.alarm_enabled,
            "ptz_enabled": cam.ptz_controller.enabled,
            "light_enabled": getattr(cam, "light_enabled", False),
            "light_on": getattr(cam, "light_is_on", False),
        }
        for idx, cam in enumerate(streams)
    ]


@app.get("/api/cameras/{camera_id}")
def get_camera_state(camera_id: int):
    cam = get_camera(camera_id)
    return {
        "id": camera_id,
        "name": cam.nombre,
        "type": cam.tipo,
        "online": bool(cam.ret and cam.frame is not None),
        "alarm_enabled": cam.alarm_enabled,
        "ptz_enabled": cam.ptz_controller.enabled,
        "light_enabled": getattr(cam, "light_enabled", False),
        "light_on": getattr(cam, "light_is_on", False),
    }


@app.get("/api/cameras/{camera_id}/snapshot.jpg")
def snapshot(camera_id: int):
    cam = get_camera(camera_id)
    frame = cam.get_processed_frame(send_alerts=False)
    if frame is None:
        raise HTTPException(status_code=503, detail="Camera offline")

    ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
    if not ok:
        raise HTTPException(status_code=500, detail="Could not encode image")

    return StreamingResponse(iter([buffer.tobytes()]), media_type="image/jpeg")


@app.post("/api/cameras/{camera_id}/alarm/toggle")
def toggle_alarm(camera_id: int):
    cam = get_camera(camera_id)
    cam.alarm_enabled = not cam.alarm_enabled
    return {"id": camera_id, "alarm_enabled": cam.alarm_enabled}


@app.post("/api/cameras/{camera_id}/light/toggle")
def toggle_light(camera_id: int):
    cam = get_camera(camera_id)
    if not getattr(cam, "light_enabled", False):
        raise HTTPException(status_code=400, detail="Light control not available for this camera")

    ok = cam.toggle_light()
    if not ok:
        raise HTTPException(status_code=502, detail="Could not update ESP32 light state")

    return {"id": camera_id, "light_on": getattr(cam, "light_is_on", False)}


@app.post("/api/cameras/{camera_id}/move")
def move_camera(camera_id: int, x: int = 0, y: int = 0):
    cam = get_camera(camera_id)
    if not cam.ptz_controller.enabled:
        raise HTTPException(status_code=400, detail="PTZ not available for this camera")

    cam.move(x, y)
    return {"ok": True, "x": x, "y": y}
