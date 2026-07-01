# -*- coding: utf-8 -*-
"""
ozon.py — маршруты Ozon.

Порядок эндпоинтов (как в Swagger):
  1. POST /ozon/card/by-id
  2. POST /ozon/card/by-url
  3. POST /ozon/raw/by-id
  4. POST /ozon/raw/by-url
  5. POST /ozon/category/info
"""

from fastapi import APIRouter, Depends

from app.api.dependencies import verify_api_key
from app.core.logging import get_logger
from app.marketplaces.ozon.service import OzonService
from app.marketplaces.ozon.schemas import (
    ParseByUrlRequest, ParseByIdRequest, CardResponse, RawResponse,
    CategoryInfoResponse, CategoryInfoRequest, CategoryInfoByIdRequest,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/ozon", tags=["Ozon"])


def get_service() -> OzonService:
    """Фабрика сервиса (можно подменить в тестах)."""
    return OzonService()


@router.post("/card/by-id", response_model=CardResponse,
             summary="Очищенная карточка по артикулу (SKU)")
def card_by_id(req: ParseByIdRequest,
               _: dict = Depends(verify_api_key),
               service: OzonService = Depends(get_service)):
    logger.info("POST /ozon/card/by-id sku=%s", req.sku)
    result = service.get_card_by_id(req.sku)
    return CardResponse(card=result["card"], debug_files=result["debug_files"])


@router.post("/card/by-url", response_model=CardResponse,
             summary="Очищенная карточка по URL")
def card_by_url(req: ParseByUrlRequest,
                _: dict = Depends(verify_api_key),
                service: OzonService = Depends(get_service)):
    logger.info("POST /ozon/card/by-url url=%s", req.url)
    result = service.get_card(req.url)
    return CardResponse(card=result["card"], debug_files=result["debug_files"])


@router.post("/raw/by-id", response_model=RawResponse,
             summary="Сырой JSON (__NUXT__) по артикулу (SKU)")
def raw_by_id(req: ParseByIdRequest,
              _: dict = Depends(verify_api_key),
              service: OzonService = Depends(get_service)):
    logger.info("POST /ozon/raw/by-id sku=%s", req.sku)
    result = service.get_raw_by_id(req.sku)
    return RawResponse(sku=result["sku"], data=result["data"], debug_files=result["debug_files"])


@router.post("/raw/by-url", response_model=RawResponse,
             summary="Сырой JSON (__NUXT__) по URL")
def raw_by_url(req: ParseByUrlRequest,
               _: dict = Depends(verify_api_key),
               service: OzonService = Depends(get_service)):
    logger.info("POST /ozon/raw/by-url url=%s", req.url)
    result = service.get_raw(req.url)
    return RawResponse(sku=result["sku"], data=result["data"], debug_files=result["debug_files"])


@router.post("/category/info", response_model=CategoryInfoResponse,
             summary="Информация о категории по URL")
def category_info(req: CategoryInfoRequest,
                  _: dict = Depends(verify_api_key),
                  service: OzonService = Depends(get_service)):
    logger.info("POST /ozon/category/info url=%s", req.url)
    info = service.get_category_info(req.url)
    return CategoryInfoResponse(
        category_id=info["category_id"],
        category_name=info["category_name"],
        offer_count=info["offer_count"],
    )


@router.post("/category/info/by-id", response_model=CategoryInfoResponse,
             summary="Информация о категории по ID")
def category_info_by_id(req: CategoryInfoByIdRequest,
                        _: dict = Depends(verify_api_key),
                        service: OzonService = Depends(get_service)):
    logger.info("POST /ozon/category/info/by-id category_id=%s", req.category_id)
    info = service.get_category_info_by_id(req.category_id)
    return CategoryInfoResponse(
        category_id=info["category_id"],
        category_name=info["category_name"],
        offer_count=info["offer_count"],
    )