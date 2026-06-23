# -*- coding: utf-8 -*-
"""
kafka_logger.py — журнал событий парсинга в Kafka.

Сюда сервис шлёт структурированные события (что парсили, сколько заняло,
успех/ошибка). Другие сервисы (аналитика, таск-менеджер) их потребляют.

ВАЖНО: Kafka — НЕ жёсткая зависимость. Если брокер недоступен или выключен
в настройках, сервис продолжает парсить, просто без журналирования.
Никаких исключений наружу отсюда не вылетает.
"""

import json
from datetime import datetime, timezone

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_producer = None
_init_failed = False


def _get_producer():
    """Лениво создаём продюсера. При неудаче помечаем и больше не пытаемся."""
    global _producer, _init_failed
    if _producer is not None or _init_failed:
        return _producer
    if not settings.kafka_enabled:
        _init_failed = True
        return None
    try:
        from kafka import KafkaProducer  # импорт здесь, чтобы не требовать пакет, если Kafka off
        _producer = KafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
            value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
            retries=1,
            request_timeout_ms=3000,
        )
        logger.info("Kafka producer инициализирован: %s", settings.kafka_bootstrap_servers)
    except Exception as e:
        logger.warning("Kafka недоступна, журналирование отключено: %s", e)
        _init_failed = True
        _producer = None
    return _producer


def emit_event(event_type: str, payload: dict) -> None:
    """
    Отправить событие в Kafka. Молча деградирует при любой проблеме.
    """
    if not settings.kafka_enabled:
        logger.debug("Kafka выключена, событие не отправлено: %s", event_type)
        return
    producer = _get_producer()
    if producer is None:
        return
    event = {
        "type": event_type,
        "ts": datetime.now(timezone.utc).isoformat(),
        "service": "parsing-service",
        "payload": payload,
    }
    try:
        producer.send(settings.kafka_topic, event)
        logger.debug("Событие отправлено в Kafka: %s", event_type)
    except Exception as e:
        logger.warning("Не удалось отправить событие в Kafka: %s", e)
