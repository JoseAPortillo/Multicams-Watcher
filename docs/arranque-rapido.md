# Arranque rapido

## 1. Clonar el proyecto

```bash
git clone <URL_DEL_REPOSITORIO>
cd Control_tplink_c200
git checkout feature/web-control-panel
```

## 2. Crear el entorno virtual

En Linux o macOS:

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

Crea `config/credentials.env` tomando como base [config/credentials_example.env](./Control_tplink_c200/config/credentials_example.env).

Valores minimos:

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

Edita [config/cameras_config.json](./Control_tplink_c200/config/cameras_config.json).

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

## 5. Arrancar la web

En Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe run_web_server.py --pc-dev
```

Alternativa:

```powershell
run_web_server_pc.bat
```

En Linux o macOS:

```bash
python run_web_server.py --pc-dev
```

El modo `--pc-dev` permite arrancar el panel sin depender de Telegram durante pruebas de escritorio.

## 6. Probar desde el movil en la misma WiFi

Si el servidor corre en el PC:

1. Obtiene la IP local del equipo
2. Abre `http://IP_DEL_PC:8000/` en el movil

En Windows puedes ver la IP con:

```powershell
ipconfig
```

Ejemplo:

```text
http://192.168.1.34:8000/
```
