@echo off
setlocal

cd /d "%~dp0.."

if not exist .venv\Scripts\python.exe (
    echo .venv\Scripts\python.exe not found
    echo Create the virtual environment first and install dependencies.
    echo.
    pause
    exit /b 1
)

.\.venv\Scripts\python.exe -m app.services.video_watcher
set "EXIT_CODE=%ERRORLEVEL%"

echo.
echo The process ended with code %EXIT_CODE%.
pause
exit /b %EXIT_CODE%
