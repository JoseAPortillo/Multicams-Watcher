# Modos de ejecucion

## 1. Web en PC para pruebas

Uso recomendado durante prototipado.

En Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe run_web_server.py --pc-dev
```

En Linux o macOS:

```bash
python run_web_server.py --pc-dev
```

Este modo:

- no exige Telegram para arrancar
- desactiva el monitor de salud por Telegram
- permite probar interfaz web, snapshots y PTZ

## 2. Web en modo simulacion

Para validar la web sin camaras reales.

En Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe run_web_server.py --pc-dev --simulate
```

Con numero concreto de camaras:

```powershell
.\.venv\Scripts\python.exe run_web_server.py --pc-dev --simulate --sim-cameras 4
```

En Linux o macOS:

```bash
python run_web_server.py --pc-dev --simulate --sim-cameras 4
```

El archivo [scripts/run_web_server_pc.bat](/d:/DEEP_CAVE_WORKS/CODE_WORKS/Control_tplink_c200/scripts/run_web_server_pc.bat) ya arranca por defecto en simulacion.

## 3. Web en Raspberry Pi

Con el entorno virtual activado:

```bash
python run_web_server.py
```

El servidor escucha por defecto en:

```text
http://0.0.0.0:8000
```

Al arrancar, el script muestra tambien las URLs utiles para acceso local y de red.

## 4. Modo local sin servidor web

Si quieres usar la aplicacion con interfaz OpenCV y sin FastAPI:

En Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m app.services.video_watcher
```

Alternativas:

```powershell
.\.venv\Scripts\python.exe .\app\services\video_watcher.py
```

```powershell
scripts\run_video_watcher.bat
```

En Linux o macOS:

```bash
python -m app.services.video_watcher
```

Este modo:

- no expone servidor HTTP
- no sirve `webapp/`
- si abre la interfaz local tipo mosaico/OpenCV
- si usa `config/credentials.env` y `config/cameras_config.json`
- si inicializa Telegram y el monitor de salud

## Comandos utiles

```bash
python run_web_server.py
python run_web_server.py --pc-dev
python run_web_server.py --pc-dev --simulate --sim-cameras 3
python -m app.services.video_watcher
```
