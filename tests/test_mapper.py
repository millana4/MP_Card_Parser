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
    # Цены присутствуют и являются числами (float), без ₽ и пробелов
    assert isinstance(card.price.card_price, float)
    assert isinstance(card.price.price, float)
    assert isinstance(card.price.original_price, float)
    # Положительные значения
    assert card.price.card_price > 0
    assert card.price.price > 0
    assert card.price.original_price > 0
    # Цена с картой не выше обычной, обычная не выше зачёркнутой
    assert card.price.card_price <= card.price.price <= card.price.original_price


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
    # У этого товара активна распродажа — остаток должен быть целым числом
    assert card.quantity is not None
    assert isinstance(card.quantity, int)
    assert card.quantity > 0


def test_variants():
    card = _load()
    assert card.variants_aspect == "Размер"
    assert len(card.variants) >= 1
    assert all(v.sku for v in card.variants)


def test_url_has_no_query():
    card = _load()
    # URL карточки должен быть без query-хвоста после '?'
    assert card.url is not None
    assert "?" not in card.url


def test_location():
    card = _load()
    # Регион выдачи должен извлечься из сырого состояния
    assert card.location is not None
    assert card.location.city
    assert card.location.country


if __name__ == "__main__":
    c = _load()
    print(json.dumps(c.model_dump(), ensure_ascii=False, indent=2))