# Deployment on Raspberry Pi 3B+ or Newer

## Recommended hardware

| Component | Recommended | Minimum |
|-----------|-------------|---------|
| RPi model | RPi 4/5 | RPi 3B+ |
| RAM | 4GB+ | 1GB |
| SD card | 64GB+ | 32GB |
| Connectivity | Ethernet | WiFi |
| Power supply | 3A+ | 2.5A |

## Software requirements

- **OS**: Raspberry Pi OS (Lite or Desktop)
- **Python**: 3.9 or newer
- **Pip**: Updated
- **Git**: To clone the repository
- **Internet connection**: For the initial installation

## Required configuration files

- `config/credentials.env` - Camera and Telegram credentials
- `config/cameras_config.json` - Camera configuration

## Remote access (optional)

- **Tailscale** if you want secure remote access. See [Remote Access with Tailscale](./acceso-remoto-tailscale.md).

## Installation from GitHub

### 1. Clone the repository

```bash
cd ~
git clone https://github.com/tu-usuario/Multicams-Watcher.git
cd Multicams-Watcher
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

**This is the longest part of the installation, around 30-60 minutes on an RPi 3B+.**

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements_rbPi.txt
```

#### Differences: requirements.txt vs requirements_rbPi.txt

| Aspect | requirements.txt | requirements_rbPi.txt |
|--------|------------------|-----------------------|
| Recommended use | PC/Development | Raspberry Pi |
| OpenCV | opencv-python (full GUI) | opencv-python (full GUI) |
| MediaPipe | v0.10.5 | v0.10.5 (prebuilt if possible) |
| Install time | ~5-10 minutes | ~30-60 minutes* |
| Disk space | ~2GB | ~2GB |

*On RPi 3B+, MediaPipe may compile from source and can take 2-3 hours. If compilation fails, use:

```bash
pip install --index-url https://www.piwheels.org/simple mediapipe
```

#### Fix for memory issues during installation

If MediaPipe compilation fails because of low memory:

```bash
# Create a temporary 2GB swap file
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Retry installation
pip install -r requirements_rbPi.txt

# Remove swap afterward (optional)
sudo swapoff /swapfile
sudo rm /swapfile
```

### 4. Configure credentials

Copy the example file and edit it with your credentials:

```bash
cp config/credentials_example.env config/credentials.env
nano config/credentials.env
```

Add your Telegram credentials and any other required configuration.

### 5. Configure cameras

Copy and customize the camera configuration file:

```bash
nano config/cameras_config.json
```

Make sure the RTSP URLs and credentials are correct for each camera.

## Running

### Manual startup

With the virtual environment activated:

```bash
python run_web_server.py
```

The server will listen on:

```text
http://0.0.0.0:8000
```

The console will show useful URLs for local and network access, for example:

```text
Local: http://127.0.0.1:8000/
Local network: http://192.168.1.X:8000/
```

### Post-installation checks

Before leaving it running in production, verify:

```bash
# Show local IP
hostname -I

# Show Tailscale IP (if installed)
tailscale ip -4

# Show listening ports
sudo netstat -tlnp | grep 8000
```

## Known limitations on RPi 3B+

**Important to know before deploying:**

| Limitation | Impact | Solution |
|------------|--------|----------|
| Maximum 2-3 simultaneous streams | Video lag with more cameras | Use lower-resolution cameras (720p) |
| Slow AI | Face detection takes 0.5-1 sec/frame | Reduce analysis FPS; do not analyze every frame |
| Few open browser tabs | Interface slows down with more than 2 browsers | Use 1 browser or Tailscale |
| Temperature | RPi heats up under continuous load | Use a heatsink and fan in warm environments |
| CPU at 100% | Poor overall performance | Monitor with `htop`; reduce FPS |

## Expected performance on RPi 3B+

**Under normal conditions:**

- **Video capture**: 20-30 fps per stream
- **Face detection**: ~0.5-1 second per frame
- **Web interface**: Responsive on the local network
- **Memory usage**: ~300-400 MB when idle
- **CPU usage**: 40-60% with 2 streams

**Usage recommendations:**

- No more than 2 simultaneous cameras
- Maximum resolution: 720p, not 1080p
- AI analysis: Enable only when needed
- Keep SSH available for remote troubleshooting
- Use Tailscale for remote access; do not expose port 8000

## Optional automatic startup with systemd

Create:

```text
/etc/systemd/system/control-camaras.service
```

Content:

```ini
[Unit]
Description=Web camera control
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/Multicams-Watcher
ExecStart=/home/pi/Multicams-Watcher/.venv/bin/python /home/pi/Multicams-Watcher/run_web_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable control-camaras.service
sudo systemctl start control-camaras.service
sudo systemctl status control-camaras.service
```

## Useful commands

```bash
# Activate virtual environment
source .venv/bin/activate

# Show local IP
hostname -I

# Show Tailscale IP
tailscale ip -4

# Monitor resources in real time
htop

# View systemd service logs
sudo journalctl -u control-camaras.service -f

# Check server status
curl http://localhost:8000/
```

## Common issues

### "No module named fastapi"

```bash
source .venv/bin/activate
pip install -r requirements_rbPi.txt
```

### A camera appears as `offline`

- Check the camera IP or RTSP URL.
- Review the RTSP username and password in `config/credentials.env`.
- Check connectivity: `ping <camera-ip>`.
- Review logs: `sudo journalctl -u control-camaras.service -n 50`.

### High CPU usage (>80%)

```bash
# Show processes by CPU usage
htop

# Reduce analysis FPS in cameras_config.json,
# or temporarily disable AI analysis
```

### MediaPipe does not compile on RPi

See the [Install dependencies](#installation-from-github) section, step 3, subsection "Fix for memory issues during installation".
