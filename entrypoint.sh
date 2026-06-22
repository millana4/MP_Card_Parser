#!/usr/bin/env bash
set -e

# Поднимаем виртуальный экран Xvfb в фоне на дисплее :99.
# Через него Chrome работает не в headless — так лучше проходит антибот.
echo "[entrypoint] Запускаю Xvfb на :99 ..."
Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp &
export DISPLAY=:99

# Небольшая пауза, чтобы Xvfb успел подняться.
sleep 1

echo "[entrypoint] Запускаю uvicorn (логи ниже) ..."
# exec — чтобы uvicorn стал основным процессом контейнера и его логи были видны
# в `docker compose logs`. --host 0.0.0.0 обязателен, иначе порт не пробросится.
exec uvicorn app:app --host 0.0.0.0 --port 8000 --log-level info
