# -*- coding: utf-8 -*-
"""
files.py — доступ к сохранённым debug-артефактам.

Эти эндпоинты имеют смысл только в режиме DEBUG (когда файлы вообще сохраняются).
В проде (DEBUG=false) папка пуста, список вернётся пустым.
"""

import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/files", tags=["Файлы (debug)"])


@router.get("", summary="Список сохранённых debug-файлов")
def list_files():
    if not os.path.isdir(settings.debug_dir):
        return {"files": []}
    files = sorted(f for f in os.listdir(settings.debug_dir) if f != ".gitkeep")
    return {"dir": settings.debug_dir, "files": files}


@router.get("/{name}", summary="Скачать debug-файл")
def get_file(name: str):
    safe = os.path.basename(name)
    path = os.path.join(settings.debug_dir, safe)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail=f"Файл не найден: {safe}")
    return FileResponse(path, filename=safe)
