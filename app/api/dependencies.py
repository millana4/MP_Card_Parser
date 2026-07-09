# -*- coding: utf-8 -*-
"""
dependencies.py — общие зависимости FastAPI.

verify_api_key — проверка межсервисного ключа (Authorization: Bearer <ключ>).
"""

from fastapi import Header, HTTPException, status

from app.core.logging import get_logger
from app.core.config import settings
from app.core.security import decode_token

logger = get_logger(__name__)


async def verify_api_key(authorization: str | None = Header(default=None)) -> dict:
    """
    Зависимость авторизации между сервисами.
    Требует заголовок 'Authorization: Bearer <ключ>' с ключом из SERVICE_API_KEY.
    """
    # ключ должен быть задан в настройках, иначе сервис незащищён — не пускаем
    if not settings.service_api_key:
        logger.error("SERVICE_API_KEY не задан — доступ закрыт")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Сервис не сконфигурирован: отсутствует SERVICE_API_KEY",
        )

    caller = decode_token(authorization)
    if not caller.get("authenticated"):
        logger.warning("Отклонён запрос: неверный или отсутствующий ключ")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )

    logger.debug("verify_api_key: доступ разрешён (%s)", caller.get("service"))
    return caller
