#!/usr/bin/env bash
set -e

echo "[entrypoint] Запускаю Xvfb на :99 ..."
Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp &
export DISPLAY=:99
sleep 1

echo "[entrypoint] Запускаю uvicorn ..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info
