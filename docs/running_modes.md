# Run Modes

## 1. Web on PC for testing

Recommended during prototyping.

On Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe run_web_server.py --pc-dev
```

On Linux or macOS:

```bash
python run_web_server.py --pc-dev
```

This mode:

- does not require Telegram to start
- disables the Telegram health monitor
- lets you test the web interface, snapshots, and PTZ

## 2. Web in simulation mode

Use this to validate the web app without real cameras.

On Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe run_web_server.py --pc-dev --simulate
```

With a specific number of cameras:

```powershell
.\.venv\Scripts\python.exe run_web_server.py --pc-dev --simulate --sim-cameras 4
```

On Linux or macOS:

```bash
python run_web_server.py --pc-dev --simulate --sim-cameras 4
```

The [scripts/run_web_server_pc.bat](../scripts/run_web_server_pc.bat) file starts in simulation mode by default.

## 3. Web on Raspberry Pi

With the virtual environment activated:

```bash
python run_web_server.py
```

By default, the server listens on:

```text
http://0.0.0.0:8000
```

On startup, the script also shows useful URLs for local and network access.

## 4. Local mode without web server

If you want to use the application with the OpenCV interface and without FastAPI:

On Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m app.services.video_watcher
```

Alternatives:

```powershell
.\.venv\Scripts\python.exe .\app\services\video_watcher.py
```

```powershell
scripts\run_video_watcher.bat
```

On Linux or macOS:

```bash
python -m app.services.video_watcher
```

This mode:

- does not expose an HTTP server
- does not serve `webapp/`
- opens the local mosaic/OpenCV-style interface
- uses `config/credentials.env` and `config/cameras_config.json`
- initializes Telegram and the health monitor

## Useful commands

```bash
python run_web_server.py
python run_web_server.py --pc-dev
python run_web_server.py --pc-dev --simulate --sim-cameras 3
python -m app.services.video_watcher
```
