# -*- coding: utf-8 -*-
"""
health.py — проверки состояния сервиса.

/health      — быстрый «жив ли сервис».
/health/ready — реальная готовность парсить: есть ли Chrome и виртуальный дисплей.
Оркестратору важно знать не «процесс запущен», а «может ли реально работать».
"""

import os
import shutil

from fastapi import APIRouter

from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Служебное"])


@router.get("/health", summary="Жив ли сервис")
def health():
    return {"status": "ok"}


@router.get("/health/ready", summary="Готов ли сервис парсить (Chrome/дисплей)")
def ready():
    chrome = shutil.which("google-chrome") or shutil.which("chromium") \
        or shutil.which("google-chrome-stable")
    display = os.environ.get("DISPLAY")
    ok = bool(chrome) and bool(display)
    logger.debug("health/ready: chrome=%s display=%s", chrome, display)
    return {
        "status": "ready" if ok else "not_ready",
        "chrome": chrome,
        "display": display,
    }
