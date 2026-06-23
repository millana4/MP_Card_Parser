# -*- coding: utf-8 -*-
"""
nuxt.py — извлечение window.__NUXT__.state из HTML.

Вынесено отдельно от parser.py намеренно: это чистая функция над строкой,
без Selenium. Так её можно тестировать на сохранённом HTML без браузера.
"""

import json

from app.core.logging import get_logger
from app.core.exceptions import ProductNotFoundError

logger = get_logger(__name__)


def extract_nuxt_state(html: str) -> dict:
    """
    Извлечь window.__NUXT__.state из HTML, раскрутив экранирование
    (\\u002F, \\", апострофы внутри текста) ручным проходом по строке.
    """
    marker = "window.__NUXT__.state"
    idx = html.find(marker)
    if idx == -1:
        has_nuxt = "__NUXT__" in html
        logger.error("__NUXT__.state не найден (есть __NUXT__: %s, длина html: %s)",
                     has_nuxt, len(html))
        raise ProductNotFoundError(
            "Не нашли window.__NUXT__.state — вероятно капча или нет данных.",
            marketplace="ozon",
        )

    eq = html.find("=", idx)
    p = eq + 1
    while p < len(html) and html[p] in " \t\r\n":
        p += 1
    quote = html[p]
    if quote not in ("'", '"'):
        raise ProductNotFoundError(
            f"Не нашли кавычку после state =, увидели: {html[p:p+30]!r}",
            marketplace="ozon",
        )

    start = p + 1
    i = start
    n = len(html)
    while i < n:
        c = html[i]
        if c == "\\":
            i += 2
            continue
        if c == quote:
            break
        i += 1
    raw = html[start:i]
    logger.debug("extract_nuxt_state: длина сырого литерала=%s", len(raw))

    try:
        decoded = raw.encode("utf-8").decode("unicode_escape").encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        decoded = json.loads(f'"{raw}"')

    data = json.loads(decoded) if isinstance(decoded, str) else decoded
    logger.debug("extract_nuxt_state: ключей верхнего уровня=%s",
                 len(data) if isinstance(data, dict) else "n/a")
    return data
