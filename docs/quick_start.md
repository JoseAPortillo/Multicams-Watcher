# Quick Start

## 1. Clone the project

```bash
git clone https://github.com/JoseAPortillo/Multicams-Watcher.git
cd Multicams-Watcher
git checkout feature/main
```

## 2. Create the virtual environment

On Linux or macOS:

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

## 3. Configure credentials

Create `config/credentials.env` using [config/credentials_example.env](../config/credentials_example.env) as a base.

Minimum values:

- `RTSP_USER`
- `RTSP_PASS`
- `TOKEN_TG`
- `CHAT_ID_TG`

If you are going to use PTZ with Tapo:

- `TAPO_USER`
- `TAPO_PASS`

Example:

```env
RTSP_USER=your_user
RTSP_PASS=your_password
TOKEN_TG=your_telegram_token
CHAT_ID_TG=your_chat_id
TAPO_USER=your_tapo_user
TAPO_PASS=your_tapo_password
```

## 4. Configure cameras

Edit [config/cameras_config.json](../config/cameras_config.json).

Example:

```json
{
  "cameras": [
    {
      "name": "Living Room",
      "type": "Tapo",
      "url_template": "rtsp://{RTSP_USER}:{RTSP_PASS}@192.168.1.153:554/stream2"
    },
    {
      "name": "Entrance",
      "type": "ESP32",
      "url": "http://192.168.1.137:81/stream"
    }
  ]
}
```

## 5. Start the web app

On Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe run_web_server.py --pc-dev
```

Alternative:

```powershell
run_web_server_pc.bat
```

On Linux or macOS:

```bash
python run_web_server.py --pc-dev
```

Alternative:

```bash
./scripts/run_web_server_rbPi.sh
```

The `--pc-dev` mode lets you start the dashboard without depending on Telegram during desktop testing.

## 6. Test from a phone on the same WiFi

If the server is running on your PC:

1. Get the local IP address of the computer.
2. Open `http://PC_IP_ADDRESS:8000/` on your phone.

On Windows you can see the IP with:

```powershell
ipconfig
```

Example:

```text
http://192.168.1.34:8000/
```
