# -*- coding: utf-8 -*-
"""
dependencies.py — общие зависимости FastAPI.

verify_api_key — проверка ключа для межсервисных вызовов.
СЕЙЧАС ЗАГЛУШКА: всегда пропускает. Логика проверки оставлена закомментированной,
чтобы в проде её включить.
"""

from fastapi import Header

from app.core.logging import get_logger
from app.core.security import decode_token

logger = get_logger(__name__)


async def verify_api_key(authorization: str | None = Header(default=None)) -> dict:
    """
    Зависимость авторизации между сервисами.

    ЗАГЛУШКА: пропускает любой запрос. В проде раскомментировать проверку.
    """
    caller = decode_token(authorization)
    logger.debug("verify_api_key: заглушка, пропускаю запрос")

    # --- ПРОД-ВАРИАНТ (пока выключен) ---
    # from fastapi import HTTPException
    # from app.core.config import settings
    # if not authorization or authorization != f"Bearer {settings.service_api_key}":
    #     raise HTTPException(status_code=401, detail="Invalid or missing API key")

    return caller
