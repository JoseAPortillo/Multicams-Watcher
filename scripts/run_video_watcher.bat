@echo off
setlocal

cd /d "%~dp0.."

if not exist .venv\Scripts\python.exe (
    echo No se encontro .venv\Scripts\python.exe
    echo Crea primero el entorno virtual e instala dependencias.
    echo.
    pause
    exit /b 1
)

.\.venv\Scripts\python.exe -m app.services.video_watcher
set "EXIT_CODE=%ERRORLEVEL%"

echo.
echo El proceso termino con codigo %EXIT_CODE%.
pause
exit /b %EXIT_CODE%
