# Control Tapo C200

Este proyecto puede ejecutarse en una Raspberry Pi como centro de control de camaras IP y exponer un panel web minimo para acceder desde movil o tablet tanto dentro como fuera de casa.

Durante el prototipado tambien puede ejecutarse desde un PC para hacer pruebas funcionales antes de pasar a la Raspberry Pi.

La forma recomendada de acceso remoto en esta rama es mediante `Tailscale`, para no exponer directamente el puerto web a Internet.

La implementacion web de esta documentacion vive en la rama:

`feature/web-control-panel`

## Funciones disponibles

- Visualizar el listado de camaras
- Ver si cada camara esta `online` u `offline`
- Abrir una camara en grande
- Ver snapshots actualizados periodicamente
- Activar o desactivar la alarma de una camara
- Mover PTZ en camaras Tapo compatibles

## Flujo recomendado de trabajo

1. Prototipar y probar desde el PC
2. Validar acceso desde movil o tablet
3. Ajustar configuracion y correcciones
4. Desplegar la misma rama en la Raspberry Pi

## Modo PC para pruebas

Esta rama incluye un modo de desarrollo para PC:

- no exige Telegram para arrancar el panel web
- desactiva el monitor de salud por Telegram
- permite probar interfaz web, snapshots y PTZ desde Windows o Linux
- incluye un modo simulacion para probar sin camaras reales

Lanzadores disponibles:

- [run_web_server.py](/d:/DEEP_CAVE_WORKS/CODE_WORKS/Control_tplink_c200/run_web_server.py)
- [run_web_server_pc.bat](/d:/DEEP_CAVE_WORKS/CODE_WORKS/Control_tplink_c200/run_web_server_pc.bat)

## Requisitos en PC o Raspberry Pi

- Python 3.11 o superior recomendado
- Las camaras y el equipo de pruebas en la misma red local
- Archivo `credentials.env` configurado
- Archivo `cameras_config.json` configurado

## Requisitos adicionales en Raspberry Pi

- Raspberry Pi 3 o superior
- Raspberry Pi OS
- Cuenta de Tailscale

## Archivos importantes

- [run_web_server.py](/d:/DEEP_CAVE_WORKS/CODE_WORKS/Control_tplink_c200/run_web_server.py)
- [server_api.py](/d:/DEEP_CAVE_WORKS/CODE_WORKS/Control_tplink_c200/app/web/server_api.py)
- [video_watcher.py](/d:/DEEP_CAVE_WORKS/CODE_WORKS/Control_tplink_c200/app/services/video_watcher.py)
- [gestion_camaras.py](/d:/DEEP_CAVE_WORKS/CODE_WORKS/Control_tplink_c200/app/cameras/gestion_camaras.py)
- [cameras_config.json](/d:/DEEP_CAVE_WORKS/CODE_WORKS/Control_tplink_c200/config/cameras_config.json)
- [credentials_example.env](/d:/DEEP_CAVE_WORKS/CODE_WORKS/Control_tplink_c200/config/credentials_example.env)

## 1. Clonar el proyecto en el PC o en la Raspberry Pi

```bash
git clone <URL_DEL_REPOSITORIO>
cd Control_tplink_c200
git checkout feature/web-control-panel
```

## 2. Crear el entorno virtual

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

En Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Configurar credenciales

Crea un archivo `config/credentials.env` tomando como base `config/credentials_example.env`.

Debes definir al menos:

- `RTSP_USER`
- `RTSP_PASS`
- `TOKEN_TG`
- `CHAT_ID_TG`

Si vas a usar PTZ en Tapo:

- `TAPO_USER`
- `TAPO_PASS`

Ejemplo:

```env
RTSP_USER=tu_usuario
RTSP_PASS=tu_password
TOKEN_TG=tu_token_de_telegram
CHAT_ID_TG=tu_chat_id
TAPO_USER=tu_usuario_tapo
TAPO_PASS=tu_password_tapo
```

## 4. Configurar camaras

Edita `config/cameras_config.json` con las IPs o URLs de tus camaras.

Ejemplo:

```json
{
  "cameras": [
    {
      "name": "Salon",
      "type": "Tapo",
      "url_template": "rtsp://{RTSP_USER}:{RTSP_PASS}@192.168.1.153:554/stream2"
    },
    {
      "name": "Entrada",
      "type": "ESP32",
      "url": "http://192.168.1.137:81/stream"
    }
  ]
}
```

## 5. Arrancar el servidor web

### Opcion A. Probar desde el PC

En Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe run_web_server.py --pc-dev
```

o directamente:

```powershell
run_web_server_pc.bat
```

En Linux o macOS:

```bash
python run_web_server.py --pc-dev
```

El modo `--pc-dev` hace que el servidor arranque aunque no quieras usar Telegram durante las pruebas.

### Opcion A2. Probar en modo simulacion

Si quieres probar toda la web sin depender de camaras reales:

En Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe run_web_server.py --pc-dev --simulate
```

Con un numero concreto de camaras simuladas:

```powershell
.\.venv\Scripts\python.exe run_web_server.py --pc-dev --simulate --sim-cameras 4
```

En Linux o macOS:

```bash
python run_web_server.py --pc-dev --simulate --sim-cameras 4
```

El archivo `run_web_server_pc.bat` ya arranca por defecto en modo simulacion.

### Opcion B. Ejecutar en Raspberry Pi

Con el entorno virtual activado:

```bash
python run_web_server.py
```

El servidor quedara escuchando por defecto en:

```text
http://0.0.0.0:8000
```

Cuando arranca, el script tambien muestra:

- URL local para el propio equipo
- URL de red local para abrir desde el movil en la misma WiFi

## 6. Probar desde el movil mientras el servidor corre en el PC

## 5B. Ejecutar la app sin servidor web

Si quieres usar la aplicacion solo en local, con la interfaz OpenCV en pantalla, sin FastAPI ni panel web, puedes arrancar el modulo de vision directamente.

En Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m app.services.video_watcher
```

En Linux o macOS:

```bash
python -m app.services.video_watcher
```

Este modo:

- no expone servidor HTTP
- no sirve la carpeta `webapp/`
- si abre la interfaz local tipo mosaico/OpenCV
- si usa `config/credentials.env` y `config/cameras_config.json`
- si inicializa Telegram y el monitor de salud

## 6. Probar desde el movil mientras el servidor corre en el PC

Si el servidor esta ejecutandose en el PC y el movil esta en la misma WiFi:

1. Localiza la IP del PC
2. Abre en el movil:

```text
http://IP_DEL_PC:8000/
```

En Windows puedes obtener la IP con:

```powershell
ipconfig
```

Busca la direccion IPv4 de tu adaptador de red, por ejemplo:

```text
192.168.1.34
```

Entonces en el movil usarias:

```text
http://192.168.1.34:8000/
```

## 7. Instalar Tailscale en el PC o en la Raspberry Pi

Para pruebas remotas fuera de la WiFi, instala Tailscale en el equipo que este ejecutando el servidor.

Durante prototipado:

- instala Tailscale en el PC
- instala Tailscale en el movil
- accede al servidor del PC por la IP Tailscale

En despliegue final:

- instala Tailscale en la Raspberry Pi
- instala Tailscale en el movil
- accede al servidor de la Raspberry por la IP Tailscale

## 8. Obtener la IP o nombre de Tailscale del equipo que ejecuta el servidor

Ejecuta:

```bash
tailscale ip -4
```

Veras una IP parecida a:

```text
100.x.x.x
```

Segun tu configuracion, tambien puede haber un nombre tipo:

```text
mi-equipo.tailnet-name.ts.net
```

Tambien puedes comprobar el nombre del equipo dentro del panel de administracion de Tailscale.

## 9. Instalar Tailscale en el movil o la tablet

En el movil o tablet:

1. Instala la app oficial de Tailscale
2. Inicia sesion con la misma cuenta o con una cuenta autorizada en la misma red Tailscale
3. Verifica que el PC o la Raspberry aparece como dispositivo conectado

## 10. Acceder desde el movil o la tablet

Con Tailscale activo en el movil, puedes entrar aunque no estes en la WiFi de casa o aunque el equipo servidor este en otra red.

Abre el navegador del movil y usa una de estas direcciones:

```text
http://100.x.x.x:8000/
```

o bien:

```text
http://mi-equipo.tailnet-name.ts.net:8000/
```

Sustituye esos valores por la IP o el nombre real asignado por Tailscale.

## Uso desde movil

- En la pantalla principal veras las camaras disponibles
- Pulsa una camara para abrir la vista principal
- Usa el boton de alarma para activarla o desactivarla
- Si la camara tiene PTZ, apareceran controles de movimiento

## Recomendaciones para pruebas en PC

- Usa `python run_web_server.py --pc-dev`
- Usa `python run_web_server.py --pc-dev --simulate` si quieres validar la web sin hardware
- Valida primero snapshots, navegacion y PTZ
- Usa Tailscale en PC y movil si quieres probar acceso remoto real antes de pasar a Raspberry
- Cuando el flujo este validado, despliega la misma rama en la Raspberry

## Recomendaciones para Raspberry Pi 3

- No abrir muchas vistas al mismo tiempo
- Mantener resoluciones de analisis moderadas
- Mantener Tailscale activo para acceso remoto
- No abrir el puerto `8000` en el router
- No exponer `FastAPI` directamente a Internet

## Arranque automatico opcional con systemd

Crea el archivo:

`/etc/systemd/system/control-camaras.service`

Con este contenido:

```ini
[Unit]
Description=Control de camaras web
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/Control_tplink_c200
ExecStart=/home/pi/Control_tplink_c200/.venv/bin/python /home/pi/Control_tplink_c200/run_web_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Luego ejecuta:

```bash
sudo systemctl daemon-reload
sudo systemctl enable control-camaras.service
sudo systemctl start control-camaras.service
sudo systemctl status control-camaras.service
```

## Comandos utiles

Activar entorno virtual:

```bash
source .venv/bin/activate
```

Lanzar servidor:

```bash
python run_web_server.py
```

Lanzar servidor en modo PC:

```bash
python run_web_server.py --pc-dev
```

Lanzar servidor en modo simulacion:

```bash
python run_web_server.py --pc-dev --simulate --sim-cameras 3
```

Ver IP de la Raspberry:

```bash
hostname -I
```

Ver IP de Tailscale:

```bash
tailscale ip -4
```

## Problemas comunes

`No module named fastapi`

Solucion:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

`La pagina no carga en el movil`

Revisa:

- que el servidor esta ejecutandose en el equipo correcto
- que Tailscale este conectado en la Raspberry
- que Tailscale este conectado en el movil
- que estas usando la IP o nombre de Tailscale correcto
- que el servidor este arrancado
- que el puerto `8000` no este bloqueado

`Quiero probar la web pero no tengo camaras disponibles`

Usa:

```bash
python run_web_server.py --pc-dev --simulate
```

`Una camara sale offline`

Revisa:

- IP de la camara
- usuario y password RTSP
- conectividad en la red local

## Estado actual

Este `README` describe la ejecucion de la rama `feature/web-control-panel`, que anade acceso web movil mediante Tailscale y tambien permite prototipado desde PC antes del despliegue final en Raspberry Pi.
