# Multicams-Watcher

Proyecto para usar una Raspberry Pi o un PC como centro de control de camaras IP, con panel web ligero para acceder desde movil o tablet.

La rama documentada aqui es:

`feature/web-control-panel`

## Que ofrece

- listado de camaras
- estado `online` / `offline`
- vista ampliada por camara
- snapshots periodicos
- activacion y desactivacion de alarma
- control PTZ en camaras Tapo compatibles
- switch de led en camaras esp32-cam compatibles.
- acceso remoto seguro con Tailscale

## Como leer esta documentacion

Este `README` queda como punto de entrada. El detalle se ha dividido en guias cortas:

- [Arranque rapido](docs/arranque-rapido.md)
- [Modos de ejecucion](docs/modos-de-ejecucion.md)
- [Acceso remoto con Tailscale](docs/acceso-remoto-tailscale.md)
- [Despliegue en Raspberry Pi](docs/raspberry-pi.md)

## Flujo recomendado

1. Probar primero en PC
2. Validar acceso desde movil o tablet
3. Ajustar configuracion
4. Desplegar en Raspberry Pi

## Requisitos minimos

- Python 3.11 o superior recomendado
- `config/credentials.env` configurado para pc.
- `config/credentials-rbPi.env` configurado para Raspberry Pi.
- `config/cameras_config.json` configurado.
- Camaras y equipo de pruebas en la misma red local.

Si vas a desplegar en Raspberry Pi:

- Raspberry Pi 3 o superior
- Raspberry Pi OS (Lite recomendado para uso sin interfaz gráfica, pero también 
  funciona con la versión completa).
- Instalación de Tailscale si quieres acceso remoto seguro.
- Cuenta de Tailscale

## Arranque rapido

Clonar el repositorio:

```bash
git clone https://github.com/JoseAPortillo/Multicams-Watcher.git
cd Multicams-Watcher
git checkout feature/main
```

Crear entorno virtual e instalar dependencias:

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

Crear `config/credentials.env` a partir de [config/credentials_example.env](./config/credentials_example.env).

Editar [config/cameras_config.json](./Multicams-Watcher/config/cameras_config.json) con tus camaras.

Ejecutar en modo PC:

```powershell
.\.venv\Scripts\python.exe run_web_server.py --pc-dev
```

Si quieres probar sin camaras reales:

```powershell
.\.venv\Scripts\python.exe run_web_server.py --pc-dev --simulate --sim-cameras 4
```

Mas detalle en [Arranque rapido](docs/arranque-rapido.md) y [Modos de ejecucion](docs/modos-de-ejecucion.md).

## Segun lo que quieras hacer

- Quiero levantar la web cuanto antes: [Arranque rapido](docs/arranque-rapido.md)
- Quiero entender `--pc-dev`, simulacion o modo local sin servidor: [Modos de ejecucion](docs/modos-de-ejecucion.md)
- Quiero entrar desde fuera de casa: [Acceso remoto con Tailscale](docs/acceso-remoto-tailscale.md)
- Quiero dejarlo corriendo en Raspberry Pi: [Despliegue en Raspberry Pi](docs/raspberry-pi.md)

## Archivos importantes

- [run_web_server.py](./Multicams-Watcher/run_web_server.py)
- [app/main/run_web_server.py](./Multicams-Watcher/app/main/run_web_server.py)
- [app/web/server_api.py](./Multicams-Watcher/app/web/server_api.py)
- [app/services/video_watcher.py](./Multicams-Watcher/app/services/video_watcher.py)
- [app/cameras/gestion_camaras.py](./Multicams-Watcher/app/cameras/gestion_camaras.py)
- [scripts/run_web_server_pc.bat](./Multicams-Watcher/scripts/run_web_server_pc.bat)
- [scripts/run_video_watcher.bat](./Multicams-Watcher/scripts/run_video_watcher.bat)


