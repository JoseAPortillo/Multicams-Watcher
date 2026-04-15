@echo off
setlocal

if not exist .venv\Scripts\python.exe (
    echo No se encontro .venv\Scripts\python.exe
    echo Crea primero el entorno virtual e instala dependencias.
    exit /b 1
)

.\.venv\Scripts\python.exe run_web_server.py --pc-dev --simulate
