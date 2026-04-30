# Configuracion de ESP32-CAM

Guia especifica para cablear, programar y conectar una ESP32-CAM AI Thinker al router WiFi.

Cuando este funcionando, la camara publicara el video en:

```text
http://IP_ASIGNADA:81/stream
```

Esa es la URL que se usa despues en `config/cameras_config.json`. La configuracion general de la app esta en `docs/arranque-rapido.md`.

## Material

- ESP32-CAM AI Thinker.
- Adaptador USB-TTL FTDI, CH340, CP2102 o similar.
- Cables Dupont.
- Fuente estable de 5 V.
- Arduino IDE con soporte para placas ESP32.

## Cableado para programar

`GPIO0` debe ir a `GND` solo mientras se graba el firmware.

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

                         GPIO0 a GND solo para grabar firmware
```

Para arrancar en modo camara normal:

```text
ESP32-CAM 5V  -> fuente 5 V
ESP32-CAM GND -> GND de la fuente
GPIO0         -> desconectado de GND
```

## Arduino IDE

Instala el soporte ESP32 en Arduino IDE usando esta URL en `File > Preferences > Additional boards manager URLs`:

```text
https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
```

Selecciona:

```text
Board: AI Thinker ESP32-CAM
Upload Speed: 115200
Partition Scheme: Huge APP
```

## Firmware

La forma mas sencilla es usar el ejemplo oficial:

```text
File > Examples > ESP32 > Camera > CameraWebServer
```

En el sketch, deja activo el modelo AI Thinker:

```cpp
#define CAMERA_MODEL_AI_THINKER
```

Y configura tu WiFi:

```cpp
const char* ssid = "TU_WIFI";
const char* password = "TU_PASSWORD";
```

El ejemplo `CameraWebServer` ya incluye el servidor HTTP necesario para:

```text
http://IP_ASIGNADA/
http://IP_ASIGNADA:81/stream
http://IP_ASIGNADA/control?var=led_intensity&val=255
http://IP_ASIGNADA/control?var=led_intensity&val=0
```

La app usa `/stream` para el video y `/control` para encender o apagar el LED flash.

## Grabar el firmware

1. Conecta el cableado de programacion.
2. Une `GPIO0` con `GND`.
3. Reinicia la ESP32-CAM con el boton `RST`.
4. Pulsa `Upload` en Arduino IDE.
5. Al terminar, desconecta `GPIO0` de `GND`.
6. Pulsa `RST` otra vez para arrancar en modo normal.

Si falla la grabacion, revisa:

```text
GPIO0 conectado a GND antes de reiniciar
TX y RX cruzados
Puerto COM correcto
Fuente estable de 5 V
Upload Speed a 115200
```

## Obtener la IP

Abre el monitor serie de Arduino IDE a `115200 baud` y reinicia la ESP32-CAM sin `GPIO0` conectado a `GND`.

Deberias ver algo parecido a:

```text
WiFi conectado
Camera Ready! Use 'http://192.168.1.137' to connect
```

La URL para la app sera:

```text
http://192.168.1.137:81/stream
```

Tambien puedes encontrar la IP desde la pagina del router, en la lista de clientes DHCP o dispositivos conectados. Suele aparecer como `espressif`, `ESP32` o similar.

Conviene reservar esa IP en el router para que no cambie.

## Prueba rapida

Con el movil o PC en la misma red WiFi:

```text
Pagina de control: http://IP_ASIGNADA/
Stream directo:    http://IP_ASIGNADA:81/stream
```

Si el stream abre en el navegador, ya puedes copiar esa URL en `config/cameras_config.json` como camara de tipo `ESP32`.

## Funcionamiento

La ESP32-CAM se conecta al router por WiFi y levanta un servidor HTTP interno:

```text
Puerto 80 -> pagina de control y comandos
Puerto 81 -> stream MJPEG
```

La app solo necesita la URL del stream. Para el LED flash, envia comandos al endpoint `/control` del firmware oficial.
