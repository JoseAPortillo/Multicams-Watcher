#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

if [ ! -d .venv ]; then
  echo "No se encontro .venv. Creando entorno virtual..."
  python3 -m venv .venv
fi

if [ ! -f .venv/bin/activate ]; then
  echo "No se encontro .venv/bin/activate"
  echo "El entorno virtual no se creo correctamente."
  exit 1
fi

source .venv/bin/activate

if [ ! -f .venv/.dependencies-installed ]; then
  echo "Instalando dependencias..."
  python -m pip install --upgrade pip setuptools wheel

  if [ -f requirements_rbPi.txt ]; then
    pip install -r requirements_rbPi.txt
  else
    pip install -r requirements.txt
  fi

  touch .venv/.dependencies-installed
fi

exec python -m app.services.video_watcher
