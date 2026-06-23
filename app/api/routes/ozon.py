# -*- coding: utf-8 -*-
"""
ozon.py — маршруты Ozon.

Порядок эндпоинтов (как в Swagger):
  1. POST /ozon/card/by-id
  2. POST /ozon/card/by-url
  3. POST /ozon/raw/by-id
  4. POST /ozon/raw/by-url
"""

from fastapi import APIRouter, Depends

from app.api.dependencies import verify_api_key
from app.core.logging import get_logger
from app.marketplaces.ozon.service import OzonService
from app.marketplaces.ozon.schemas import (
    ParseByUrlRequest, ParseByIdRequest, CardResponse, RawResponse,
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
    logger.info("POST /ozon/card/by-id sku=%s region=%s", req.sku, req.region)
    result = service.get_card_by_id(req.sku, region=req.region)
    return CardResponse(card=result["card"], debug_files=result["debug_files"])


@router.post("/card/by-url", response_model=CardResponse,
             summary="Очищенная карточка по URL")
def card_by_url(req: ParseByUrlRequest,
                _: dict = Depends(verify_api_key),
                service: OzonService = Depends(get_service)):
    logger.info("POST /ozon/card/by-url url=%s region=%s", req.url, req.region)
    result = service.get_card(req.url, region=req.region)
    return CardResponse(card=result["card"], debug_files=result["debug_files"])


@router.post("/raw/by-id", response_model=RawResponse,
             summary="Сырой JSON (__NUXT__) по артикулу (SKU)")
def raw_by_id(req: ParseByIdRequest,
              _: dict = Depends(verify_api_key),
              service: OzonService = Depends(get_service)):
    logger.info("POST /ozon/raw/by-id sku=%s region=%s", req.sku, req.region)
    result = service.get_raw_by_id(req.sku, region=req.region)
    return RawResponse(sku=result["sku"], data=result["data"], debug_files=result["debug_files"])


@router.post("/raw/by-url", response_model=RawResponse,
             summary="Сырой JSON (__NUXT__) по URL")
def raw_by_url(req: ParseByUrlRequest,
               _: dict = Depends(verify_api_key),
               service: OzonService = Depends(get_service)):
    logger.info("POST /ozon/raw/by-url url=%s region=%s", req.url, req.region)
    result = service.get_raw(req.url, region=req.region)
    return RawResponse(sku=result["sku"], data=result["data"], debug_files=result["debug_files"])