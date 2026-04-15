import cv2
import time
import threading
from pathlib import Path

import telepot
from telepot.loop import MessageLoop

from app.cameras import camera_config, gestion_camaras, health_monitor
from app.cameras.simulated_cameras import build_simulated_streams
from app.core.constants import WINDOW_NAME
from app.core.settings import CAMERAS_CONFIG_FILE, CREDENTIALS_FILE
from app.services import display, telegram_cmds


def load_credentials(env_path: Path, require_telegram: bool = True, require_rtsp: bool = True):
    values = {}
    if env_path.exists():
        with env_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, val = line.split("=", 1)
                values[key.strip()] = val.strip().strip('"').strip("'")
    elif require_rtsp or require_telegram:
        raise RuntimeError(f"Missing credentials file: {env_path}")

    required = []
    if require_rtsp:
        required.extend(["RTSP_USER", "RTSP_PASS"])
    if require_telegram:
        required.extend(["TOKEN_TG", "CHAT_ID_TG"])
    missing = [key for key in required if not values.get(key)]
    if missing:
        raise RuntimeError(f"Missing required credentials in {env_path}: {', '.join(missing)}")

    values.setdefault("RTSP_USER", "")
    values.setdefault("RTSP_PASS", "")
    values.setdefault("TOKEN_TG", "")
    values.setdefault("CHAT_ID_TG", "")
    return values


def build_streams(env_vars: dict, simulate: bool = False, simulated_count: int = 3):
    if simulate:
        return build_simulated_streams(count=simulated_count)

    camera_env_values = {
        "RTSP_USER": env_vars["RTSP_USER"],
        "RTSP_PASS": env_vars["RTSP_PASS"],
    }

    cameras = camera_config.load_camera_config(CAMERAS_CONFIG_FILE)["cameras"]
    return [
        camera_config.make_camera_stream(
            cam,
            env_vars["TOKEN_TG"],
            env_vars["CHAT_ID_TG"],
            camera_env_values,
            gestion_camaras.GestionCamara,
            tapo_user=env_vars.get("TAPO_USER"),
            tapo_pass=env_vars.get("TAPO_PASS"),
        )
        for cam in cameras
    ]


def bootstrap_system(require_telegram: bool = True, simulate: bool = False, simulated_count: int = 3):
    env_vars = load_credentials(
        CREDENTIALS_FILE,
        require_telegram=require_telegram,
        require_rtsp=not simulate,
    )
    streams = build_streams(env_vars, simulate=simulate, simulated_count=simulated_count)
    return env_vars, streams


def run_ui_loop(streams: list):
    touch_manager = display.TouchManager()
    cv2.namedWindow(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    cv2.setMouseCallback(WINDOW_NAME, touch_manager.touch_callback, {"streams": streams})

    try:
        while True:
            canvas = display.render_fullscreen(touch_manager.max_camera) if touch_manager.max_camera else display.render_mosaic(streams)
            cv2.imshow(WINDOW_NAME, canvas)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        for s in streams:
            s.stop()
        cv2.destroyAllWindows()


def main():
    env_vars, streams = bootstrap_system()
    bot = telepot.Bot(env_vars["TOKEN_TG"])

    MessageLoop(bot, lambda msg: telegram_cmds.handle_telegram_message(msg, bot, streams, env_vars["CHAT_ID_TG"])).run_as_thread()
    threading.Thread(
        target=health_monitor.monitor_cameras_health,
        args=(streams, bot, env_vars["CHAT_ID_TG"]),
        daemon=True,
    ).start()

    print("Sugerencia: Escribe /ayuda en tu bot de Telegram.")
    print("INITIALIZING SYSTEM. Press 'q' to exit.")
    time.sleep(2)

    run_ui_loop(streams)


if __name__ == "__main__":
    main()
