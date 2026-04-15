from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent
APP_DIR = PACKAGE_DIR.parent
PROJECT_ROOT = APP_DIR.parent

CONFIG_DIR = PROJECT_ROOT / "config"
ASSETS_DIR = PROJECT_ROOT / "assets"
MODELS_DIR = ASSETS_DIR / "models"
WEBAPP_DIR = PROJECT_ROOT / "webapp"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

CREDENTIALS_FILE = CONFIG_DIR / "credentials.env"
CAMERAS_CONFIG_FILE = CONFIG_DIR / "cameras_config.json"
FACE_MODEL_FILE = MODELS_DIR / "face_detector.task"
POSE_MODEL_FILE = MODELS_DIR / "pose_landmarker.task"
