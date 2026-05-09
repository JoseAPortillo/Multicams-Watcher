import atexit
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Dict, Any

import cv2
import telepot
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.cameras import camera_config, gestion_camaras, health_monitor
from app.core.settings import WEBAPP_DIR
from app.services.video_watcher import bootstrap_system
from app.cameras.network_scanner import scan_cameras
from app.cameras.camera_config import load_camera_config
import json
from urllib.parse import urlparse


DEV_DISABLE_TELEGRAM = os.getenv("CONTROL_APP_DISABLE_TELEGRAM", "").lower() in {"1", "true", "yes", "on"}
DEV_DISABLE_HEALTH_MONITOR = os.getenv("CONTROL_APP_DISABLE_HEALTH_MONITOR", "").lower() in {"1", "true", "yes", "on"}
SIMULATION_MODE = os.getenv("CONTROL_APP_SIMULATE", "").lower() in {"1", "true", "yes", "on"}
SIMULATED_CAMERA_COUNT = int(os.getenv("CONTROL_APP_SIM_CAMERA_COUNT", "3"))

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "cameras_config.json"
DEFAULT_ALERT_COOLDOWN_SECONDS = 10

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


def extract_camera_ip(camera: Dict[str, Any]) -> str | None:
    url = camera.get("url") or camera.get("url_template") or ""
    if not url:
        return camera.get("ip")

    parsed = urlparse(url)
    if parsed.hostname:
        return parsed.hostname
    return camera.get("ip")


def configured_camera_payload(camera: Dict[str, Any], camera_id: int) -> Dict[str, Any]:
    ip = extract_camera_ip(camera)
    return {
        "id": camera_id,
        "name": camera.get("name", f"{camera.get('type', 'Camera')} {ip or camera_id}"),
        "type": camera.get("type", "unknown"),
        "ip": ip,
        "url": camera.get("url"),
        "url_template": camera.get("url_template"),
        "alert_cooldown_seconds": camera.get("alert_cooldown_seconds", DEFAULT_ALERT_COOLDOWN_SECONDS),
    }


def save_camera_config(config: Dict[str, Any]) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def update_runtime_camera_name(camera_id: int, new_name: str) -> None:
    if camera_id >= len(streams):
        return

    streams[camera_id].nombre = new_name
    streams[camera_id].ptz_controller.camera_name = new_name
    streams[camera_id].light_controller.camera_name = new_name
    streams[camera_id].health_monitor.camera_name = new_name


def update_runtime_camera_alert_cooldown(camera_id: int, alert_cooldown_seconds: float) -> None:
    if camera_id >= len(streams):
        return

    streams[camera_id].alert_service.cooldown = alert_cooldown_seconds


def configured_ips(cameras_config: List[Dict[str, Any]]) -> set[str]:
    return {
        ip
        for ip in (extract_camera_ip(camera) for camera in cameras_config)
        if ip
    }


def running_stream_ips() -> set[str]:
    return {
        ip
        for ip in (extract_camera_ip({"url": getattr(stream, "url", "")}) for stream in streams)
        if ip
    }


def make_runtime_stream(camera: Dict[str, Any]):
    camera_env_values = {
        "RTSP_USER": env_vars["RTSP_USER"],
        "RTSP_PASS": env_vars["RTSP_PASS"],
        "ALERT_COOLDOWN_SECONDS": env_vars["ALERT_COOLDOWN_SECONDS"],
    }
    return camera_config.make_camera_stream(
        camera,
        env_vars["TOKEN_TG"],
        env_vars["CHAT_ID_TG"],
        camera_env_values,
        gestion_camaras.GestionCamara,
        tapo_user=env_vars.get("TAPO_USER"),
        tapo_pass=env_vars.get("TAPO_PASS"),
    )


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
    cameras_config = load_camera_config(str(CONFIG_PATH)).get("cameras", [])
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
            "alert_cooldown_seconds": cameras_config[idx].get("alert_cooldown_seconds", getattr(cam, "cooldown", DEFAULT_ALERT_COOLDOWN_SECONDS))
            if idx < len(cameras_config)
            else getattr(cam, "cooldown", DEFAULT_ALERT_COOLDOWN_SECONDS),
        }
        for idx, cam in enumerate(streams)
    ]


@app.get("/api/camera-config")
def list_camera_config():
    config = load_camera_config(str(CONFIG_PATH))
    cameras_config = config.get("cameras", [])
    return {
        "cameras": [
            configured_camera_payload(camera, idx)
            for idx, camera in enumerate(cameras_config)
        ]
    }


@app.patch("/api/camera-config/{camera_id}")
def update_camera_config(camera_id: int, payload: Dict[str, Any]):
    """Update editable camera config fields and persist them immediately."""
    try:
        config = load_camera_config(str(CONFIG_PATH))
        cameras_config = config.get("cameras", [])
        if camera_id < 0 or camera_id >= len(cameras_config):
            raise HTTPException(status_code=404, detail="Camera not found")

        camera = cameras_config[camera_id]
        updated_fields = {}

        if "name" in payload:
            new_name = str(payload.get("name", "")).strip()
            if not new_name:
                raise HTTPException(status_code=400, detail="Camera name cannot be empty")
            camera["name"] = new_name
            update_runtime_camera_name(camera_id, new_name)
            updated_fields["name"] = new_name

        if "alert_cooldown_seconds" in payload:
            try:
                alert_cooldown_seconds = float(payload.get("alert_cooldown_seconds"))
            except (TypeError, ValueError):
                raise HTTPException(status_code=400, detail="Alert cooldown must be a number")
            if alert_cooldown_seconds < 0 or alert_cooldown_seconds > 3600:
                raise HTTPException(status_code=400, detail="Alert cooldown must be between 0 and 3600 seconds")
            camera["alert_cooldown_seconds"] = round(alert_cooldown_seconds, 2)
            update_runtime_camera_alert_cooldown(camera_id, camera["alert_cooldown_seconds"])
            updated_fields["alert_cooldown_seconds"] = camera["alert_cooldown_seconds"]

        if not updated_fields:
            raise HTTPException(status_code=400, detail="No editable fields provided")

        config["cameras"] = cameras_config
        save_camera_config(config)
        return configured_camera_payload(camera, camera_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")


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
    frame = cam.get_processed_frame()
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


@app.get("/api/scan-cameras")
def scan_network():
    """Scan network for cameras asynchronously."""
    try:
        detected = scan_cameras()
        config = load_camera_config(str(CONFIG_PATH))
        cameras_config = config.get("cameras", [])
        excluded_ips = configured_ips(cameras_config) | running_stream_ips()

        result = []
        seen_ips = set()
        for cam in detected:
            cam_ip = cam.get("ip")
            if not cam_ip or cam_ip in excluded_ips or cam_ip in seen_ips:
                continue
            cam["registered"] = False
            cam["detected"] = True
            result.append(cam)
            seen_ips.add(cam_ip)

        return {"cameras": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


@app.post("/api/update-cameras")
def update_cameras(payload: Dict[str, Any]):
    """Update cameras config with cameras to add and remove."""
    try:
        config = load_camera_config(str(CONFIG_PATH))
        cameras_config = config.get("cameras", [])

        cameras_to_add = payload.get("add", [])
        cameras_to_remove = payload.get("remove", [])
        cameras_to_rename = payload.get("rename", [])

        for item in cameras_to_rename:
            camera_id = item.get("id")
            new_name = str(item.get("name", "")).strip()
            if isinstance(camera_id, int) and 0 <= camera_id < len(cameras_config) and new_name:
                cameras_config[camera_id]["name"] = new_name
                update_runtime_camera_name(camera_id, new_name)

        if cameras_to_remove:
            remove_ids = {
                cam.get("id")
                for cam in cameras_to_remove
                if isinstance(cam.get("id"), int)
            }
            remove_ips = set()
            for cam in cameras_to_remove:
                ip = extract_camera_ip(cam)
                if ip:
                    remove_ips.add(ip)

            kept_cameras = []
            removed_indexes = []
            for idx, camera in enumerate(cameras_config):
                camera_ip = extract_camera_ip(camera)
                should_remove = idx in remove_ids or (camera_ip and camera_ip in remove_ips)
                if should_remove:
                    removed_indexes.append(idx)
                else:
                    kept_cameras.append(camera)
            cameras_config = kept_cameras

            for idx in sorted(removed_indexes, reverse=True):
                if idx < len(streams):
                    streams[idx].stop()
                    streams.pop(idx)

        # Add new cameras
        added_cameras = []
        for cam in cameras_to_add:
            # Check if not already registered
            is_duplicate = False
            cam_url = cam.get("url") or cam.get("url_template", "")
            for existing in cameras_config:
                existing_url = existing.get("url") or existing.get("url_template", "")
                if cam_url and existing_url and cam_url == existing_url:
                    is_duplicate = True
                    break

            if not is_duplicate:
                new_cam = {
                    "name": f"{cam['type']} {cam['ip']}",
                    "type": cam["type"],
                    "alert_cooldown_seconds": DEFAULT_ALERT_COOLDOWN_SECONDS,
                }
                if cam["type"] == "ESP32":
                    new_cam["url"] = cam["url"]
                elif cam["type"] == "Tapo":
                    new_cam["url_template"] = cam["url_template"]
                cameras_config.append(new_cam)
                added_cameras.append(new_cam)

        config["cameras"] = cameras_config

        save_camera_config(config)

        for camera in added_cameras:
            streams.append(make_runtime_stream(camera))

        return {
            "message": "Config updated successfully.",
            "added": len(added_cameras),
            "removed": len(cameras_to_remove),
            "renamed": len(cameras_to_rename),
            "cameras_total": len(streams),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")
