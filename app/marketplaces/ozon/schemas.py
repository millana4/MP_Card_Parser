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


# ============================================================================ #
#  Category info schemas                                                       #
# ============================================================================ #


class CategoryInfoByUrlRequest(BaseModel):
    """Запрос на получение информации о категории."""
    url: str = Field(
        ...,
        description="URL категории Ozon",
        examples=["https://www.ozon.ru/category/byustgaltery-zhenskie-31307/"],
    )


class CategoryInfoResponse(BaseModel):
    """Ответ с информацией о категории."""
    ok: bool = True
    category_id: int | None = Field(None, description="ID категории")
    category_name: str | None = Field(None, description="Название категории")
    offer_count: int | None = Field(None, description="Количество товаров в категории")


class CategoryInfoByIdRequest(BaseModel):
    """Запрос на получение информации о категории по её ID."""
    category_id: str = Field(
        ...,
        description="ID категории Ozon",
        examples=["31307"],
    )