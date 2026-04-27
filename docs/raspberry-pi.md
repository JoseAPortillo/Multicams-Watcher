# Despliegue en Raspberry Pi

## Requisitos

- Raspberry Pi 3 o superior
- Raspberry Pi OS (versión Lite, recomendado)
- entorno virtual configurado
- `config/credentials.env`
- `config/cameras_config.json`
- Tailscale instalado si quieres acceso remoto seguro

## Instalación desde GitHub

### 1. Clonar el repositorio

```bash
cd ~
git clone https://github.com/tu-usuario/Multicams-Watcher.git
cd Multicams-Watcher
```

### 2. Crear entorno virtual

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configurar credenciales

Copia el archivo de ejemplo y edítalo con tus credenciales:

```bash
cp config/credentials_example.env config/credentials.env
nano config/credentials.env
```

Añade tus credenciales de Telegram y otras configuraciones necesarias.

### 5. Configurar cámaras

Copia y personaliza el archivo de configuración de cámaras:

```bash
nano config/cameras_config.json
```

Asegúrate de que las URLs RTSP y credenciales sean correctas para cada cámara.

## Ejecucion manual

Con el entorno virtual activado:

```bash
python run_web_server.py
```

## Recomendaciones para Raspberry Pi 3

- no abrir muchas vistas al mismo tiempo
- mantener resoluciones de analisis moderadas
- mantener Tailscale activo para acceso remoto
- no abrir el puerto `8000` en el router

## Arranque automatico opcional con systemd

Crea:

`/etc/systemd/system/control-camaras.service`

Contenido:

```ini
[Unit]
Description=Control de camaras web
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/Multicams-Watcher
ExecStart=/home/pi/Multicams-Watcher/.venv/bin/python /home/pi/Multicams-Watcher/run_web_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Luego:

```bash
sudo systemctl daemon-reload
sudo systemctl enable control-camaras.service
sudo systemctl start control-camaras.service
sudo systemctl status control-camaras.service
```

## Comandos utiles

```bash
source .venv/bin/activate
hostname -I
tailscale ip -4
```

## Problemas comunes

`No module named fastapi`

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Una camara sale `offline`:

- revisa IP o URL
- revisa usuario y password RTSP
- revisa conectividad local
