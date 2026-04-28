# Acceso remoto con Tailscale

## Cuándo usarlo

Es la opción **recomendada** para entrar desde fuera de casa sin exponer FastAPI ni el puerto 8000 a Internet.

## Comparativa: Acceso local vs Tailscale

| Aspecto | Acceso local (WiFi) | Tailscale (Remoto) |
|--------|-------------------|-------------------|
| Red requerida | Misma WiFi/LAN | Ninguna (VPN privada) |
| Seguridad | Básica (LAN local) | Muy alta (encriptada) |
| Latencia | <5ms | 50-200ms (típico) |
| Configuración router | No requerida | No requerida |
| Exposición a Internet | No | No (VPN privada) |
| Funciona 4G/5G | No | Sí |

## Flujo recomendado

### Durante prototipado en PC

1. Instala Tailscale en el PC de desarrollo
2. Instala Tailscale en tu móvil
3. Accede por la IP de Tailscale del PC desde cualquier lugar
4. Ideal para pruebas remotas sin servidor

### En despliegue final en Raspberry Pi

1. Instala Tailscale en la Raspberry Pi
2. Instala Tailscale en tu móvil/PC remoto
3. Accede por la IP de Tailscale de la RPi desde cualquier lugar
4. Producción segura sin exponer puerto 8000

## Instalación en PC (desarrollo)

### Windows

1. Descarga desde [tailscale.com](https://tailscale.com/download)
2. Instala y ejecuta
3. Abre https://login.tailscale.com en el navegador
4. Sigue los pasos de autenticación

### macOS/Linux

```bash
# Instalar
brew install tailscale

# Conectar
sudo tailscale up
```

## Instalación en Raspberry Pi 3B+

### Prerrequisitos

- Raspberry Pi con Raspberry Pi OS
- Acceso SSH
- Conexión a internet
- Cuenta de Tailscale gratuita

### Pasos de instalación

1. **Agregar repositorio de Tailscale**

```bash
curl -fsSL https://pkgs.tailscale.com/stable/raspberry-pi.html | bash
```

2. **Instalar Tailscale**

```bash
sudo apt-get install tailscale
```

3. **Iniciar y habilitar el servicio**

```bash
sudo systemctl enable --now tailscaled
```

4. **Conectar a tu red Tailscale**

```bash
sudo tailscale up
```

Verás una URL para autenticarte. Cópiala en el navegador.

5. **Verificar conexión**

```bash
tailscale status
```

Deberías ver algo como:
```
100.x.x.x       raspberry-pi      your-user@...  linux   -
```

### Post-instalación en RPi

- Tailscale se ejecutará como servicio automático en segundo plano
- La RPi será accesible desde cualquier dispositivo en tu red Tailscale
- Se reinicia automáticamente tras reboot

## Obtener la IP de Tailscale

En el equipo que ejecuta el servidor (PC o RPi):

```bash
tailscale ip -4
```

Verás una IP similar a:
```
100.x.x.x
```

También puedes usar el nombre del dispositivo:
```
raspberry-pi.tailnet-XXXXXXXX.ts.net
```

## Acceso desde el móvil o PC remoto

1. **Instala Tailscale** en tu móvil/PC remoto
2. **Activa Tailscale** y autentica con la misma cuenta
3. **Abre cualquiera de estas URLs:**

```
http://100.x.x.x:8000/
http://mi-dispositivo.tailnet-name.ts.net:8000/
```

Ejemplo real:
```
http://100.123.45.67:8000/
http://raspberry-pi.tailnet-abcd1234.ts.net:8000/
```

## Recomendaciones de seguridad

✅ **Hacer:**
- Usar Tailscale para acceso remoto (recomendado)
- Validar primero en red local (192.168.x.x), luego por Tailscale
- Mantener Tailscale actualizado

❌ **NO hacer:**
- No abras puerto 8000 en el router (vulnerable)
- No expongas FastAPI directamente a Internet
- No compartas URLs de Tailscale públicamente
- No desactives autenticación de Tailscale

## Troubleshooting

### "La página no carga"

```bash
# Verificar que el servidor está corriendo
curl http://localhost:8000/

# Verificar que Tailscale está conectado
tailscale status

# Verificar IP actual
tailscale ip -4
```

Causas comunes:
- Servidor no corriendo en el dispositivo correcto
- Tailscale desconectado en algún dispositivo
- IP de Tailscale cambió (usar nombre de dispositivo es más estable)
- Puerto 8000 bloqueado por firewall local

### "Tailscale conecta pero sin internet"

```bash
# Reiniciar Tailscale
sudo systemctl restart tailscaled

# En Windows
tailscale logout
tailscale up
```

### "Reautenticación requerida"

```bash
# Desconectar y reconectar
tailscale logout
tailscale up

# En RPi (con sudo)
sudo tailscale logout
sudo tailscale up
```

### "Servicio no inicia en RPi"

```bash
# Ver logs de error
sudo journalctl -u tailscaled -n 50

# Reiniciar servicio
sudo systemctl restart tailscaled
```

## Monitoreo de Tailscale

Ver dispositivos conectados:
```bash
tailscale status
```

Ver tráfico:
```bash
tailscale netcheck
```

Configuración:
```bash
tailscale prefs show
```
