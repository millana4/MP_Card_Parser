# -*- coding: utf-8 -*-
"""
test_mapper.py — тесты преобразования сырого HTML в карточку.

Работают на СОХРАНЁННОМ HTML (фикстуре), без обращения к Ozon. Это позволяет
менять логику извлечения и мгновенно проверять, что поля собираются верно,
не дёргая сайт и не воюя с антиботом.

Запуск:  pytest tests/ -v
"""

import os
import json

from app.marketplaces.ozon.mapper import build_card
from app.marketplaces.ozon.nuxt import extract_nuxt_state

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures",
                       "ozon_plate_zolla_4439072345.html")


def _load():
    html = open(FIXTURE, encoding="utf-8").read()
    nuxt = extract_nuxt_state(html)
    return build_card(html, nuxt, "https://www.ozon.ru/product/plate-zolla-4439072345/")


def test_basic_fields():
    card = _load()
    assert card.sku == "4439072345"
    assert card.name == "Платье Zolla"
    assert card.brand == "Zolla"


def test_prices():
    card = _load()
    assert card.price.card_price
    assert card.price.price
    assert card.price.original_price
    # Цены — только цифры, без ₽ и пробелов
    assert card.price.card_price.isdigit()
    assert card.price.price.isdigit()
    assert card.price.original_price.isdigit()


def test_seller_with_ogrn():
    card = _load()
    assert card.seller.id
    assert card.seller.ogrn  # ОГРН должен извлечься


def test_characteristics():
    card = _load()
    assert "Сезон" in card.characteristics
    assert "Состав материала" in card.characteristics


def test_quantity():
    card = _load()
    # У этого товара активна распродажа — остаток должен быть числом-строкой
    assert card.quantity is not None
    assert card.quantity.isdigit()


def test_variants():
    card = _load()
    assert card.variants_aspect == "Размер"
    assert len(card.variants) >= 1
    assert all(v.sku for v in card.variants)


if __name__ == "__main__":
    c = _load()
    print(json.dumps(c.model_dump(), ensure_ascii=False, indent=2))