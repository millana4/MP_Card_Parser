# -*- coding: utf-8 -*-
"""
logging.py — единая настройка логирования.

Уровень берётся из настроек (LOG_LEVEL). Формат включает имя логгера,
чтобы было видно, из какого модуля пришло сообщение.

Договорённость по уровням (используется по всему сервису):
  DEBUG   — детальный ход выполнения: входы в функции, промежуточные значения.
  INFO    — ключевые шаги: старт парсинга, успех, какой товар.
  WARNING — нештатные, но не фатальные ситуации: не нашли поле, сработал ретрай.
  ERROR   — ошибки, из-за которых операция не выполнена: блокировка, краш драйвера.
"""

import sys
import logging

from app.core.config import settings


def setup_logging() -> None:
    """Сконфигурировать корневой логгер один раз при старте приложения."""
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
    logging.getLogger(__name__).debug("Логирование настроено, уровень=%s", settings.log_level)


def get_logger(name: str) -> logging.Logger:
    """Получить именованный логгер для модуля."""
    return logging.getLogger(name)
