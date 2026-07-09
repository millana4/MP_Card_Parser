from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)

# схема безопасности — Swagger по ней нарисует кнопку "Authorize"
bearer_scheme = HTTPBearer(auto_error=False)


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    """Проверка межсервисного ключа (Authorization: Bearer <ключ>)."""
    if not settings.service_api_key:
        logger.error("SERVICE_API_KEY не задан — доступ закрыт")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Сервис не сконфигурирован: отсутствует SERVICE_API_KEY",
        )
    # credentials.credentials — это то, что после "Bearer "
    if credentials is None or credentials.credentials != settings.service_api_key:
        logger.warning("Отклонён запрос: неверный или отсутствующий ключ")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    logger.debug("verify_api_key: доступ разрешён")
    return {"service": "task-manager", "authenticated": True}
