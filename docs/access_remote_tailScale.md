# Remote Access with Tailscale

## When to use it

This is the **recommended** option for accessing the app from outside your home without exposing FastAPI or port 8000 to the Internet.

## Comparison: Local access vs Tailscale

| Aspect | Local access (WiFi) | Tailscale (Remote) |
|--------|---------------------|--------------------|
| Required network | Same WiFi/LAN | None (private VPN) |
| Security | Basic (local LAN) | Very high (encrypted) |
| Latency | <5ms | 50-200ms (typical) |
| Router configuration | Not required | Not required |
| Internet exposure | No | No (private VPN) |
| Works on 4G/5G | No | Yes |

## Recommended flow

### During PC prototyping

1. Install Tailscale on the development PC.
2. Install Tailscale on your phone.
3. Access the PC's Tailscale IP from anywhere.
4. Ideal for remote testing without a server.

### In the final Raspberry Pi deployment

1. Install Tailscale on the Raspberry Pi.
2. Install Tailscale on your phone or remote PC.
3. Access the RPi's Tailscale IP from anywhere.
4. Safe production access without exposing port 8000.

## Installation on PC (development)

### Windows

1. Download it from [tailscale.com](https://tailscale.com/download).
2. Install and run it.
3. Open https://login.tailscale.com in your browser.
4. Follow the authentication steps.

### macOS/Linux

```bash
# Install
brew install tailscale

# Connect
sudo tailscale up
```

## Installation on Raspberry Pi 3B+

### Prerequisites

- Raspberry Pi with Raspberry Pi OS
- SSH access
- Internet connection
- Free Tailscale account

### Installation steps

1. **Add the Tailscale repository**

```bash
curl -fsSL https://pkgs.tailscale.com/stable/raspberry-pi.html | bash
```

2. **Install Tailscale**

```bash
sudo apt-get install tailscale
```

3. **Start and enable the service**

```bash
sudo systemctl enable --now tailscaled
```

4. **Connect to your Tailscale network**

```bash
sudo tailscale up
```

You will see a URL to authenticate. Copy it into your browser.

5. **Verify the connection**

```bash
tailscale status
```

You should see something like:

```text
100.x.x.x       raspberry-pi      your-user@...  linux   -
```

### Post-installation on RPi

- Tailscale will run as an automatic background service.
- The RPi will be accessible from any device in your Tailscale network.
- It restarts automatically after a reboot.

## Get the Tailscale IP

On the device running the server, either PC or RPi:

```bash
tailscale ip -4
```

You will see an IP similar to:

```text
100.x.x.x
```

You can also use the device name:

```text
raspberry-pi.tailnet-XXXXXXXX.ts.net
```

## Access from a phone or remote PC

1. **Install Tailscale** on your phone or remote PC.
2. **Enable Tailscale** and authenticate with the same account.
3. **Open any of these URLs:**

```text
http://100.x.x.x:8000/
http://my-device.tailnet-name.ts.net:8000/
```

Real example:

```text
http://100.123.45.67:8000/
http://raspberry-pi.tailnet-abcd1234.ts.net:8000/
```

## Security recommendations

**Do:**

- Use Tailscale for remote access (recommended).
- Validate first on the local network (192.168.x.x), then through Tailscale.
- Keep Tailscale updated.

**Do not:**

- Do not open port 8000 on the router; it is vulnerable.
- Do not expose FastAPI directly to the Internet.
- Do not share Tailscale URLs publicly.
- Do not disable Tailscale authentication.

## Troubleshooting

### "The page does not load"

```bash
# Verify that the server is running
curl http://localhost:8000/

# Verify that Tailscale is connected
tailscale status

# Verify the current IP
tailscale ip -4
```

Common causes:

- Server not running on the correct device.
- Tailscale disconnected on one of the devices.
- Tailscale IP changed; using the device name is more stable.
- Port 8000 blocked by the local firewall.

### "Tailscale connects but there is no internet"

```bash
# Restart Tailscale
sudo systemctl restart tailscaled

# On Windows
tailscale logout
tailscale up
```

### "Reauthentication required"

```bash
# Disconnect and reconnect
tailscale logout
tailscale up

# On RPi, with sudo
sudo tailscale logout
sudo tailscale up
```

### "Service does not start on RPi"

```bash
# View error logs
sudo journalctl -u tailscaled -n 50

# Restart service
sudo systemctl restart tailscaled
```

## Monitoring Tailscale

Show connected devices:

```bash
tailscale status
```

Show traffic diagnostics:

```bash
tailscale netcheck
```

Configuration:

```bash
tailscale prefs show
```
