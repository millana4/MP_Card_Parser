# -*- coding: utf-8 -*-
"""
security.py — работа с токеном межсервисной авторизации.

Сейчас декодирование — заглушка: возвращает фиктивный «контекст вызывающего».
В проде здесь будет реальная проверка/декодирование JWT или сверка ключа.
"""

from app.core.logging import get_logger

logger = get_logger(__name__)


def decode_token(token: str | None) -> dict:
    """
    Декодировать токен вызывающего сервиса.

    ЗАГЛУШКА: ничего не проверяет, возвращает условный контекст.
    В проде заменить на реальную валидацию.
    """
    logger.debug("decode_token: получен токен длиной %s", len(token) if token else 0)
    return {"service": "unknown", "authenticated": False}
