# Acceso remoto con Tailscale

## Cuando usarlo

Es la opcion recomendada para entrar desde fuera de casa sin exponer `FastAPI` ni el puerto `8000` a Internet.

## Flujo recomendado

Durante prototipado:

- instala Tailscale en el PC
- instala Tailscale en el movil
- accede por la IP o el nombre de Tailscale del PC

En despliegue final:

- instala Tailscale en la Raspberry Pi
- instala Tailscale en el movil
- accede por la IP o el nombre de Tailscale de la Raspberry

## Obtener la IP de Tailscale

En el equipo que ejecuta el servidor:

```bash
tailscale ip -4
```

Veras una IP similar a:

```text
100.x.x.x
```

Tambien puedes usar el nombre del dispositivo dentro de tu red Tailscale, por ejemplo:

```text
mi-equipo.tailnet-name.ts.net
```

## Acceso desde el movil

Con Tailscale activo en el movil, abre una de estas URLs:

```text
http://100.x.x.x:8000/
http://mi-equipo.tailnet-name.ts.net:8000/
```

## Recomendaciones

- no abras el puerto `8000` en el router
- no expongas `FastAPI` directamente a Internet
- valida primero en red local y luego por Tailscale

## Problemas comunes

La pagina no carga:

- confirma que el servidor esta corriendo en el equipo correcto
- revisa que Tailscale este conectado en ambos dispositivos
- verifica que la IP o el nombre usado sea el actual
- comprueba que el puerto `8000` no este bloqueado
