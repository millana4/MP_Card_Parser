# -*- coding: utf-8 -*-
"""
app.py — веб-сервис поверх card_parser.py (FastAPI + Swagger).

Что даёт:
  - POST /parse  — принимает URL карточки Ozon, парсит, возвращает JSON с данными
                   товара. Дополнительно кладёт на диск полный HTML и JSON.
  - GET  /files  — список сохранённых файлов в папке output.
  - GET  /files/{name} — скачать конкретный файл (html или json).
  - Swagger UI доступен на /docs (открывается в браузере).

Запуск локально:
    uvicorn app:app --host 0.0.0.0 --port 8000
    затем открыть http://localhost:8000/docs

В Docker — см. docker_card_parser_README.md (сервис card-api).

Переиспользует движок OzonCardParser из card_parser.py — никакой логики
парсинга здесь не дублируется.
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
    description="Парсинг карточек товаров маркетплейсов. Сейчас поддержан Ozon "
                "(эндпоинт /parse/ozon): вводишь URL — получаешь сырые данные из "
                "__NUXT__ в JSON. HTML и JSON дополнительно сохраняются на диск. "
                "Другие маркетплейсы будут добавлены отдельными эндпоинтами.",
    version="1.0.0",
)

# Selenium не потокобезопасен, а сервис может получать запросы конкурентно.
# Поэтому сериализуем доступ: один парсинг за раз. Для исследовательских целей
# (ручные одиночные запросы через Swagger) этого достаточно.
_parse_lock = threading.Lock()


class ParseRequest(BaseModel):
    url: str = Field(
        ...,
        description="URL карточки товара Ozon",
        examples=["https://www.ozon.ru/product/bryuki-dlya-malyshey-leratutti-3169084399/"],
    )


class ParseByIdRequest(BaseModel):
    sku: str = Field(
        ...,
        description="Артикул (SKU) товара Ozon — число из адреса карточки",
        examples=["3169084399"],
    )


class ParseResponse(BaseModel):
    ok: bool
    tag: str | None = None
    json_file: str | None = None
    html_file: str | None = None
    data: dict | None = None
    error: str | None = None


def _run_parse(url: str) -> ParseResponse:
    """Общая логика: по готовому URL спарсить карточку и собрать ответ."""
    url = url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Пустой URL/SKU")

    # Один парсинг за раз (Selenium не потокобезопасен).
    with _parse_lock:
        parser = None
        try:
            parser = OzonCardParser()
            result = parser.parse_card_full(url)
            return ParseResponse(
                ok=True,
                tag=result["tag"],
                json_file=os.path.basename(result["json_path"]),
                html_file=os.path.basename(result["html_path"]),
                data=result["data"],
            )
        except Exception as e:
            logging.error(f"❌ Ошибка парсинга: {e}", exc_info=True)
            return ParseResponse(ok=False, error=str(e))
        finally:
            if parser:
                parser.close()


@app.get("/", summary="Проверка, что сервис жив")
def root():
    return {"status": "ok", "swagger": "/docs"}


@app.post("/parse/ozon", response_model=ParseResponse, tags=["Ozon"],
          summary="Распарсить карточку Ozon по URL")
def parse_ozon(req: ParseRequest):
    """
    Парсинг карточки **Ozon** по URL.

    Принимает URL карточки, открывает её в браузере (Selenium + stealth),
    достаёт встроенный объект __NUXT__ и возвращает данные товара в JSON.

    Дополнительно сохраняет в папке output два файла с именами
    `ozon_<sku>_<дата_время>`: .html (полная страница) и .json (данные товара).
    Их можно скачать через GET /files/{name}.
    """
    return _run_parse(req.url)


@app.post("/parse/ozon/by-id", response_model=ParseResponse, tags=["Ozon"],
          summary="Распарсить карточку Ozon по артикулу (SKU)")
def parse_ozon_by_id(req: ParseByIdRequest):
    """
    Парсинг карточки **Ozon** по артикулу (SKU).

    Из артикула собирается короткий адрес `https://www.ozon.ru/product/<sku>/`,
    Ozon сам перенаправляет на полную карточку. Дальше — то же, что и парсинг
    по URL: данные из __NUXT__ + сохранение .html и .json в output.
    """
    sku = req.sku.strip()
    if not sku.isdigit():
        raise HTTPException(
            status_code=400,
            detail=f"SKU должен быть числом (артикул из адреса карточки). Получено: {sku!r}",
        )
    url = f"https://www.ozon.ru/product/{sku}/"
    return _run_parse(url)


@app.get("/files", summary="Список сохранённых файлов")
def list_files():
    """Показать, какие файлы лежат в папке output (html, json, debug-скриншоты)."""
    if not os.path.isdir(OUTPUT_DIR):
        return {"files": []}
    files = sorted(os.listdir(OUTPUT_DIR))
    return {"dir": OUTPUT_DIR, "files": files}


@app.get("/files/{name}", summary="Скачать файл из output")
def get_file(name: str):
    """Скачать конкретный файл (html / json / png) по имени из папки output."""
    # Защита от выхода из папки (path traversal).
    safe_name = os.path.basename(name)
    path = os.path.join(OUTPUT_DIR, safe_name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail=f"Файл не найден: {safe_name}")
    return FileResponse(path, filename=safe_name)
