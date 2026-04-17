# Despliegue en Raspberry Pi

## Requisitos

- Raspberry Pi 3 o superior
- Raspberry Pi OS
- entorno virtual configurado
- `config/credentials.env`
- `config/cameras_config.json`
- Tailscale instalado si quieres acceso remoto seguro

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
WorkingDirectory=/home/pi/Control_tplink_c200
ExecStart=/home/pi/Control_tplink_c200/.venv/bin/python /home/pi/Control_tplink_c200/run_web_server.py
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
