# Multicams-Watcher

Project for using a Raspberry Pi or PC as an IP camera control center, with a lightweight web dashboard accessible from a phone or tablet.

The documented branch is:

`feature/web-control-panel`

## What it offers

- camera list
- `online` / `offline` status
- expanded view per camera
- periodic snapshots
- alarm activation and deactivation
- PTZ control on compatible Tapo cameras
- LED switch on compatible ESP32-CAM cameras
- secure remote access with Tailscale

## How to read this documentation

This `README` is the entry point. Details are split into short guides:

- [Quick Start](docs/quick_start.md)
- [Run Modes](docs/running_modes.md)
- [Remote Access with Tailscale](docs/access_remote_tailScale.md)
- [Raspberry Pi Deployment](docs/raspberry-pi.md)

## Recommended flow

1. Test on PC first.
2. Validate access from a phone or tablet.
3. Adjust configuration.
4. Deploy on Raspberry Pi.

## Minimum requirements

- Python 3.11 or newer recommended
- `config/credentials.env` configured for PC
- `config/credentials-rbPi.env` configured for Raspberry Pi
- `config/cameras_config.json` configured
- Cameras and test device on the same local network

If you are deploying on Raspberry Pi:

- Raspberry Pi 3 or newer
- Raspberry Pi OS (Lite recommended for headless use, though the full version also works)
- Tailscale installed if you want secure remote access
- Tailscale account

## Quick start

Clone the repository:

```bash
git clone https://github.com/JoseAPortillo/Multicams-Watcher.git
cd Multicams-Watcher
git checkout feature/main
```

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

On Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create `config/credentials.env` from [config/credentials_example.env](./config/credentials_example.env).

Edit [config/cameras_config.json](./config/cameras_config.json) with your cameras.

Run in PC mode:

```powershell
.\.venv\Scripts\python.exe run_web_server.py --pc-dev
```

If you want to test without real cameras:

```powershell
.\.venv\Scripts\python.exe run_web_server.py --pc-dev --simulate --sim-cameras 4
```

More detail in [Quick Start](docs/quick_start.md) and [Run Modes](docs/running_modes.md).

## Depending on what you want to do

- I want to start the web app as soon as possible: [Quick Start](docs/quick_start.md)
- I want to understand `--pc-dev`, simulation, or local mode without a server: [Run Modes](docs/running_modes.md)
- I want to access it from outside my home: [Remote Access with Tailscale](docs/access_remote_tailScale.md)
- I want to leave it running on Raspberry Pi: [Raspberry Pi Deployment](docs/raspberry-pi.md)

## Important files

- [run_web_server.py](./run_web_server.py)
- [app/main/run_web_server.py](./app/main/run_web_server.py)
- [app/web/server_api.py](./app/web/server_api.py)
- [app/services/video_watcher.py](./app/services/video_watcher.py)
- [app/cameras/gestion_camaras.py](./app/cameras/gestion_camaras.py)
- [scripts/run_web_server_pc.bat](./scripts/run_web_server_pc.bat)
- [scripts/run_video_watcher.bat](./scripts/run_video_watcher.bat)
