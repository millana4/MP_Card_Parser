#!/usr/bin/env bash
set -e

echo "[entrypoint] Запускаю Xvfb на :99 ..."
Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp &
export DISPLAY=:99
sleep 1

echo "[entrypoint] Запускаю команду $@"
exec "$@"
