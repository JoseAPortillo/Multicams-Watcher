# ESP32-CAM Configuration

Specific guide for wiring, flashing, and connecting an ESP32-CAM AI Thinker to your WiFi router.

When it is working, the camera will publish the video at:

```text
http://ASSIGNED_IP:81/stream
```

That is the URL later used in `config/cameras_config.json`. The general app configuration is in `docs/arranque-rapido.md`.

## Materials

- ESP32-CAM AI Thinker.
- USB-TTL adapter: FTDI, CH340, CP2102, or similar.
- Dupont wires.
- Stable 5 V power supply.
- Arduino IDE with ESP32 board support.

## Wiring for flashing

`GPIO0` must be connected to `GND` only while flashing the firmware.

```text
          USB-TTL / FTDI                    ESP32-CAM AI Thinker
        +----------------+                 +----------------------+
        |            5V  |---------------->|  5V                  |
        |           GND  |---------------->|  GND                 |
        |            TX  |---------------->|  U0R / RX0           |
        |            RX  |<----------------|  U0T / TX0           |
        +----------------+                 |                      |
                                           |  GPIO0               |
                                           |    |                 |
                                           |    +---------------->| GND
                                           +----------------------+

                         GPIO0 to GND only while flashing firmware
```

To boot in normal camera mode:

```text
ESP32-CAM 5V  -> 5 V power supply
ESP32-CAM GND -> power supply GND
GPIO0         -> disconnected from GND
```

## Arduino IDE

Install ESP32 support in Arduino IDE using this URL in `File > Preferences > Additional boards manager URLs`:

```text
https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
```

Select:

```text
Board: AI Thinker ESP32-CAM
Upload Speed: 115200
Partition Scheme: Huge APP
```

## Firmware

The easiest option is to use the official example:

```text
File > Examples > ESP32 > Camera > CameraWebServer
```

In the sketch, keep the AI Thinker model enabled:

```cpp
#define CAMERA_MODEL_AI_THINKER
```

Then configure your WiFi:

```cpp
const char* ssid = "YOUR_WIFI";
const char* password = "YOUR_PASSWORD";
```

The `CameraWebServer` example already includes the HTTP server needed for:

```text
http://ASSIGNED_IP/
http://ASSIGNED_IP:81/stream
http://ASSIGNED_IP/control?var=led_intensity&val=255
http://ASSIGNED_IP/control?var=led_intensity&val=0
```

The app uses `/stream` for video and `/control` to turn the flash LED on or off.

## Flash the firmware

1. Connect the programming wiring.
2. Connect `GPIO0` to `GND`.
3. Reset the ESP32-CAM with the `RST` button.
4. Press `Upload` in Arduino IDE.
5. When it finishes, disconnect `GPIO0` from `GND`.
6. Press `RST` again to boot in normal mode.

If flashing fails, check:

```text
GPIO0 connected to GND before reset
TX and RX crossed
Correct COM port
Stable 5 V power supply
Upload Speed set to 115200
```

## Get the IP

Open the Arduino IDE serial monitor at `115200 baud` and reset the ESP32-CAM without `GPIO0` connected to `GND`.

You should see something like:

```text
WiFi connected
Camera Ready! Use 'http://192.168.1.137' to connect
```

The URL for the app will be:

```text
http://192.168.1.137:81/stream
```

You can also find the IP from the router page, in the DHCP client list or connected devices list. It usually appears as `espressif`, `ESP32`, or similar.

It is useful to reserve that IP in the router so it does not change.

## Quick test

With your phone or PC on the same WiFi network:

```text
Control page:  http://ASSIGNED_IP/
Direct stream: http://ASSIGNED_IP:81/stream
```

If the stream opens in the browser, you can copy that URL into `config/cameras_config.json` as an `ESP32` camera.

## How it works

The ESP32-CAM connects to the router over WiFi and starts an internal HTTP server:

```text
Port 80 -> control page and commands
Port 81 -> MJPEG stream
```

The app only needs the stream URL. For the flash LED, it sends commands to the official firmware's `/control` endpoint.
