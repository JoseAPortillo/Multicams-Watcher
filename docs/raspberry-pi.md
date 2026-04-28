# Despliegue en Raspberry Pi 3B+ o superior

## Hardware recomendado

| Componente | Recomendado | Mínimo |
|-----------|-------------|--------|
| Modelo RPi | RPi 4/5 | RPi 3B+ |
| RAM | 4GB+ | 1GB |
| Tarjeta SD | 64GB+ | 32GB |
| Conectividad | Ethernet | WiFi |
| Fuente | 3A+ | 2.5A |

## Requisitos de software

- **SO**: Raspberry Pi OS (Lite o Desktop)
- **Python**: 3.9 o superior
- **Pip**: Actualizado
- **Git**: Para clonar el repositorio
- **Conexión a internet**: Para instalación inicial

## Archivos de configuración necesarios

- `config/credentials.env` - Credenciales de cámaras y Telegram
- `config/cameras_config.json` - Configuración de cámaras

## Acceso remoto (opcional)

- **Tailscale** si deseas acceso remoto seguro (ver [Acceso remoto con Tailscale](./4-acceso-remoto-tailscale.md))

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

**Esta es la parte más larga de la instalación (~30-60 minutos en RPi 3B+)**

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements_rbPi.txt
```

#### Diferencias: requirements.txt vs requirements_rbPi.txt

| Aspecto | requirements.txt | requirements_rbPi.txt |
|---------|------------------|-----------------------|
| Uso recomendado | PC/Desarrollo | Raspberry Pi |
| OpenCV | opencv-python (GUI completo) | opencv-python (GUI completo) |
| MediaPipe | v0.10.5 | v0.10.5 (precompilado si es posible) |
| Tiempo instalación | ~5-10 minutos | ~30-60 minutos* |
| Espacio ocupado | ~2GB | ~2GB |

*En RPi 3B+, MediaPipe compila desde fuentes y puede tardar 2-3 horas. Si falla la compilación, usa:
```bash
pip install --index-url https://www.piwheels.org/simple mediapipe
```

#### Solución si hay problemas de memoria durante instalación

Si la compilación de MediaPipe falla por falta de memoria:

```bash
# Crear swap temporal de 2GB
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Reintentar instalación
pip install -r requirements_rbPi.txt

# Eliminar swap después (opcional)
sudo swapoff /swapfile
sudo rm /swapfile
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

## Ejecución

### Arranque manual

Con el entorno virtual activado:

```bash
python run_web_server.py
```

El servidor escuchará en:
```
http://0.0.0.0:8000
```

Verás en consola las URLs útiles para acceso local y de red, ejemplo:
```
Local: http://127.0.0.1:8000/
Red local: http://192.168.1.X:8000/
```

### Verificación post-instalación

Antes de dejar corriendo en producción, verifica:

```bash
# Ver IP local
hostname -I

# Ver IP de Tailscale (si instalado)
tailscale ip -4

# Ver puertos escuchando
sudo netstat -tlnp | grep 8000
```

## Limitaciones conocidas de RPi 3B+

⚠️ **Importante conocer antes de desplegar:**

| Limitación | Impacto | Solución |
|-----------|--------|----------|
| Máximo 2-3 streams simultáneos | Video lag con más cámaras | Usar cámaras con resolución menor (720p) |
| IA lenta | Detección facial tarda 0.5-1 seg/frame | Reducir fps de análisis, no analizar todas las frames |
| Pocas pestañas web abiertas | Interfaz lenta con >2 navegadores | Usar 1 navegador o Tailscale |
| Temperatura | RPi se calienta con carga continua | Usar disipador, ventilador si clima cálido |
| CPU al 100% | Bajo rendimiento general | Monitorear con `htop`, reducir fps |

## Performance esperado en RPi 3B+

**Bajo condiciones normales:**

- **Captura de video**: 20-30 fps por stream
- **Detección facial**: ~0.5-1 segundo por frame
- **Interfaz web**: Responsive en red local
- **Consumo de memoria**: ~300-400 MB (en idle)
- **Consumo de CPU**: 40-60% (con 2 streams)

**Recomendaciones de uso:**

- No más de 2 cámaras simultáneamente
- Resoluciones máximas: 720p (no 1080p)
- Análisis de IA: Activar solo cuando sea necesario
- Mantener SSH abierto para troubleshooting remoto
- Usar Tailscale para acceso remoto (no exponer puerto 8000)

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

## Comandos útiles

```bash
# Activar entorno virtual
source .venv/bin/activate

# Ver IP local
hostname -I

# Ver IP de Tailscale
tailscale ip -4

# Monitorear recursos en tiempo real
htop

# Ver logs del servicio systemd
sudo journalctl -u control-camaras.service -f

# Ver estado del servidor
curl http://localhost:8000/
```

## Problemas comunes

### "No module named fastapi"

```bash
source .venv/bin/activate
pip install -r requirements_rbPi.txt
```

### Una cámara sale `offline`

- Verifica IP o URL RTSP de la cámara
- Revisa usuario y contraseña RTSP en `config/credentials.env`
- Comprueba conectividad: `ping <ip-camara>`
- Revisa logs: `sudo journalctl -u control-camaras.service -n 50`

### Alto consumo de CPU (>80%)

```bash
# Ver procesos por CPU
htop

# Reducir fps de análisis en cameras_config.json
# o desactivar análisis de IA temporalmente
```

### MediaPipe no compila en RPi

Ver sección de [Instalar dependencias](#instalación-desde-github) punto 3, subsección "Solución si hay problemas de memoria durante instalación".