import cv2
import time
import threading
from pathlib import Path

import telepot
from telepot.loop import MessageLoop

import camera_config
import display
import telegram_cmds
import health_monitor
import GestionCamaras
from constants import WINDOW_NAME

CONFIG_DIR = Path(__file__).resolve().parent
CREDENTIALS_FILE = CONFIG_DIR / "credentials.env"
CAMERAS_CONFIG_FILE = CONFIG_DIR / "cameras_config.json"


def load_credentials(env_path: Path):
    values = {}
    with env_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            values[key.strip()] = val.strip().strip('"').strip("'")

    required = ["RTSP_USER", "RTSP_PASS", "TOKEN_TG", "CHAT_ID_TG"]
    missing = [key for key in required if not values.get(key)]
    if missing:
        raise RuntimeError(f"Missing required credentials in {env_path}: {', '.join(missing)}")
    return values


def build_streams(env_vars: dict):
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
            GestionCamaras.GestionCamara,
            tapo_user=env_vars.get("TAPO_USER"),
            tapo_pass=env_vars.get("TAPO_PASS"),
        )
        for cam in cameras
    ]


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
    env_vars = load_credentials(CREDENTIALS_FILE)
    bot = telepot.Bot(env_vars["TOKEN_TG"])
    streams = build_streams(env_vars)

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
