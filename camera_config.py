"""
Camera configuration management and setup.
Handles loading cameras from JSON and building URLs.
"""
import os
import json
from typing import Dict, List, Any


def require_env(name: str) -> str:
    """Get required environment variable or raise error."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def load_camera_config(config_path: str) -> Dict[str, Any]:
    """Load camera configuration from JSON file."""
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_env_values() -> Dict[str, str]:
    """Get all required environment values for URL templating."""
    return {
        "RTSP_USER": require_env("RTSP_USER"),
        "RTSP_PASS": require_env("RTSP_PASS")
    }


def resolve_camera_url(cam: Dict[str, Any], env_values: Dict[str, str]) -> str:
    """
    Resolve camera URL from config.
    Prefers explicit 'url' field, falls back to 'url_template' with env substitution.
    """
    if "url" in cam and cam["url"]:
        return cam["url"]
    elif "url_template" in cam:
        return cam["url_template"].format(**env_values)
    else:
        raise ValueError(f"Camera '{cam.get('name', 'unknown')}' has no URL or URL template")


def make_camera_stream(cam: Dict[str, Any], token_tg: str, chat_id_tg: str, 
                      env_values: Dict[str, str], GestionCamara_class,
                      tapo_user: str = None, tapo_pass: str = None):
    """
    Create and start a camera stream from config.
    
    Args:
        cam: Camera config dict
        token_tg: Telegram bot token
        chat_id_tg: Telegram chat ID
        env_values: Dict with RTSP_USER, RTSP_PASS, etc.
        GestionCamara_class: The GestionCamara class to instantiate
        tapo_user: Optional Tapo username for PTZ control
        tapo_pass: Optional Tapo password for PTZ control
    
    Returns:
        Started camera stream instance
    """
    url = resolve_camera_url(cam, env_values)
    camera_type = cam.get("type", "tapo")
    
    return GestionCamara_class(
        cam["name"],
        url,
        token_tg,
        chat_id_tg,
        tipo=camera_type,
        tapo_user=tapo_user,
        tapo_pass=tapo_pass,
    ).start()
