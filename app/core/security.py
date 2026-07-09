# -*- coding: utf-8 -*-
"""
security.py — работа с токеном межсервисной авторизации.

Сверяет Bearer-токен из заголовка Authorization с ключом из настроек.
"""

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


def decode_token(token: str | None) -> dict:
    """
    Проверить токен вызывающего сервиса.

    Ожидается заголовок вида 'Bearer <ключ>'. Возвращает контекст вызывающего;
    поле authenticated=True только при совпадении ключа. Само решение
    пропускать/отклонять принимает verify_api_key в dependencies.py.
    """
    if not token:
        logger.debug("decode_token: токен отсутствует")
        return {"service": "unknown", "authenticated": False}

    # ожидаем "Bearer <ключ>"
    expected = f"Bearer {settings.service_api_key}"
    if settings.service_api_key and token == expected:
        return {"service": "task-manager", "authenticated": True}

    logger.debug("decode_token: токен не совпал с ключом")
    return {"service": "unknown", "authenticated": False}