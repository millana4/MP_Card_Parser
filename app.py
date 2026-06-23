"""
app.py — веб-сервис Card Parser API (FastAPI + Swagger).

Эндпоинты делятся на две группы:

  СЫРЫЕ данные (полный JSON из __NUXT__):
    POST /parse/ozon            — по URL
    POST /parse/ozon/by-id      — по артикулу (SKU)

  ОЧИЩЕННЫЕ данные (структурированная карточка):
    POST /parse/ozon/card       — по URL
    POST /parse/ozon/card/by-id — по артикулу (SKU)

Парсинг внутри общий: страница открывается один раз, на диск сохраняются
html, сырой json и json карточки. Сырые эндпоинты отдают сырьё, card-эндпоинты —
структурированную карточку.

Файлы из output можно посмотреть через /files и скачать через /files/{name}.
Swagger UI — на /docs.
"""

import os
import threading
import logging

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from card_parser import OzonCardParser, OUTPUT_DIR

app = FastAPI(
    title="Card Parser API",
    description="Парсинг карточек товаров маркетплейсов. Сейчас поддержан Ozon. "
                "Есть эндпоинты для сырых данных (__NUXT__) и для очищенной "
                "структурированной карточки — по URL и по артикулу (SKU).",
    version="2.0.0",
)

# Selenium не потокобезопасен — один парсинг за раз.
_parse_lock = threading.Lock()


# --------------------------------------------------------------------------- #
#  Модели запроса/ответа                                                       #
# --------------------------------------------------------------------------- #
class ParseRequest(BaseModel):
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


class RawResponse(BaseModel):
    """Ответ сырых эндпоинтов: полный JSON из __NUXT__."""
    ok: bool
    tag: str | None = None
    json_file: str | None = None
    html_file: str | None = None
    data: dict | None = None
    error: str | None = None


class CardResponse(BaseModel):
    """Ответ card-эндпоинтов: структурированная карточка."""
    ok: bool
    tag: str | None = None
    card_file: str | None = None
    card: dict | None = None
    error: str | None = None


# --------------------------------------------------------------------------- #
#  Общая логика парсинга                                                       #
# --------------------------------------------------------------------------- #
def _parse(url: str) -> dict:
    """
    Открывает карточку один раз, сохраняет файлы (html, сырой json, card json)
    и возвращает результат: {tag, json_path, html_path, card_path, data, card}.
    """
    url = url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Пустой URL/SKU")

    with _parse_lock:
        parser = None
        try:
            parser = OzonCardParser()
            return parser.parse_card_full(url)
        finally:
            if parser:
                parser.close()


def _id_to_url(sku: str) -> str:
    """Собирает короткий URL карточки из артикула. Ozon редиректит на полный."""
    sku = sku.strip()
    if not sku.isdigit():
        raise HTTPException(
            status_code=400,
            detail=f"SKU должен быть числом (артикул из адреса карточки). Получено: {sku!r}",
        )
    return f"https://www.ozon.ru/product/{sku}/"


# --------------------------------------------------------------------------- #
#  Служебные эндпоинты                                                         #
# --------------------------------------------------------------------------- #
@app.get("/", summary="Проверка, что сервис жив")
def root():
    return {"status": "ok", "swagger": "/docs"}


# --------------------------------------------------------------------------- #
#  СЫРЫЕ данные                                                                #
# --------------------------------------------------------------------------- #
@app.post("/parse/ozon", response_model=RawResponse, tags=["Ozon — сырые данные"],
          summary="Сырой JSON по URL")
def parse_ozon_raw(req: ParseRequest):
    """Открывает карточку Ozon по URL и возвращает полный сырой JSON из __NUXT__.
    Дополнительно сохраняет html и json в папку output."""
    try:
        r = _parse(req.url)
        return RawResponse(
            ok=True,
            tag=r["tag"],
            json_file=os.path.basename(r["json_path"]),
            html_file=os.path.basename(r["html_path"]),
            data=r["data"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ Ошибка парсинга: {e}", exc_info=True)
        return RawResponse(ok=False, error=str(e))


@app.post("/parse/ozon/by-id", response_model=RawResponse, tags=["Ozon — сырые данные"],
          summary="Сырой JSON по артикулу (SKU)")
def parse_ozon_raw_by_id(req: ParseByIdRequest):
    """То же, что /parse/ozon, но карточка задаётся артикулом (SKU)."""
    try:
        r = _parse(_id_to_url(req.sku))
        return RawResponse(
            ok=True,
            tag=r["tag"],
            json_file=os.path.basename(r["json_path"]),
            html_file=os.path.basename(r["html_path"]),
            data=r["data"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ Ошибка парсинга: {e}", exc_info=True)
        return RawResponse(ok=False, error=str(e))


# --------------------------------------------------------------------------- #
#  ОЧИЩЕННЫЕ данные (структурированная карточка)                               #
# --------------------------------------------------------------------------- #
@app.post("/parse/ozon/card", response_model=CardResponse, tags=["Ozon — карточка"],
          summary="Очищенная карточка по URL")
def parse_ozon_card(req: ParseRequest):
    """Открывает карточку Ozon по URL и возвращает структурированные данные
    (название, цены, характеристики, рейтинг, продавец с ОГРН и пр.).
    Дополнительно сохраняет файл *_card.json в папку output."""
    try:
        r = _parse(req.url)
        return CardResponse(
            ok=True,
            tag=r["tag"],
            card_file=os.path.basename(r["card_path"]) if r.get("card_path") else None,
            card=r.get("card"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ Ошибка парсинга: {e}", exc_info=True)
        return CardResponse(ok=False, error=str(e))


@app.post("/parse/ozon/card/by-id", response_model=CardResponse, tags=["Ozon — карточка"],
          summary="Очищенная карточка по артикулу (SKU)")
def parse_ozon_card_by_id(req: ParseByIdRequest):
    """То же, что /parse/ozon/card, но карточка задаётся артикулом (SKU)."""
    try:
        r = _parse(_id_to_url(req.sku))
        return CardResponse(
            ok=True,
            tag=r["tag"],
            card_file=os.path.basename(r["card_path"]) if r.get("card_path") else None,
            card=r.get("card"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ Ошибка парсинга: {e}", exc_info=True)
        return CardResponse(ok=False, error=str(e))


# --------------------------------------------------------------------------- #
#  Файлы                                                                       #
# --------------------------------------------------------------------------- #
@app.get("/files", summary="Список сохранённых файлов")
def list_files():
    if not os.path.isdir(OUTPUT_DIR):
        return {"files": []}
    return {"dir": OUTPUT_DIR, "files": sorted(os.listdir(OUTPUT_DIR))}


@app.get("/files/{name}", summary="Скачать файл из output")
def get_file(name: str):
    safe_name = os.path.basename(name)
    path = os.path.join(OUTPUT_DIR, safe_name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail=f"Файл не найден: {safe_name}")
    return FileResponse(path, filename=safe_name)
