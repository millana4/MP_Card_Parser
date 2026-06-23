# -*- coding: utf-8 -*-
"""
schemas.py — схемы API для Ozon (вход/выход эндпоинтов).

Отделены от доменных models.py: схемы описывают контракт HTTP, модели —
бизнес-сущности. Менять формат ответа можно не трогая домен.
"""

from pydantic import BaseModel, Field

from app.marketplaces.ozon.models import OzonCard


class ParseByUrlRequest(BaseModel):
    url: str = Field(
        ...,
        description="URL карточки товара Ozon",
        examples=["https://www.ozon.ru/product/plate-zarina-3641521371/"],
    )


class ParseByIdRequest(BaseModel):
    sku: str = Field(
        ...,
        description="Артикул (SKU) товара Ozon — число из адреса карточки",
        examples=["3641521371"],
    )


class CardResponse(BaseModel):
    """Ответ с очищенной структурированной карточкой."""
    ok: bool = True
    card: OzonCard | None = None
    debug_files: dict[str, str] | None = Field(
        default=None,
        description="Имена сохранённых файлов (только в режиме DEBUG)",
    )


class RawResponse(BaseModel):
    """Ответ с сырым JSON из __NUXT__."""
    ok: bool = True
    sku: str | None = None
    data: dict | None = None
    debug_files: dict[str, str] | None = Field(
        default=None,
        description="Имена сохранённых файлов (только в режиме DEBUG)",
    )