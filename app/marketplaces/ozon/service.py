# -*- coding: utf-8 -*-
"""
service.py — бизнес-логика парсинга Ozon (оркестратор).

Дирижирует слоями, сам ничего не парсит и не извлекает:
  1) репозиторий достаёт сырьё (html + nuxt_state);
  2) mapper превращает сырьё в доменную карточку OzonCard;
  3) при DEBUG сохраняются артефакты (html/json/png) на диск;
  4) в Kafka уходит событие о результате (если включено).

Возвращает структуры, удобные для эндпоинтов (карточка / сырьё + debug-файлы).
"""

import os
import json
import time
from datetime import datetime

from app.core.config import settings, MarketplacePolicy
from app.core.exceptions import AntibotBlockedError
from app.core.logging import get_logger
from app.marketplaces.ozon.repository import OzonRepository
from app.marketplaces.ozon.mapper import build_card
from app.shared.kafka_logger import emit_event

logger = get_logger(__name__)


class OzonService:
    def __init__(self, policy: MarketplacePolicy | None = None):
        self.policy = policy or settings.ozon_policy()
        self.repo = OzonRepository(self.policy)

    # ------------------------------------------------------------------ #
    def _basename(self, url: str) -> str:
        sku = OzonRepository.sku_from_url(url) or datetime.now().strftime("%Y%m%d_%H%M%S")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"ozon_{sku}_{ts}"

    def _save_debug(self, base: str, raw: dict, card_dict: dict | None) -> dict:
        """Сохранить артефакты в debug_dir. Только при settings.debug."""
        if not settings.debug:
            return {}
        os.makedirs(settings.debug_dir, exist_ok=True)
        files: dict[str, str] = {}

        html_path = os.path.join(settings.debug_dir, f"{base}.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(raw["html"])
        files["html"] = os.path.basename(html_path)

        json_path = os.path.join(settings.debug_dir, f"{base}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(raw["nuxt_state"], f, ensure_ascii=False, indent=2)
        files["json"] = os.path.basename(json_path)

        if card_dict is not None:
            card_path = os.path.join(settings.debug_dir, f"{base}_card.json")
            with open(card_path, "w", encoding="utf-8") as f:
                json.dump(card_dict, f, ensure_ascii=False, indent=2)
            files["card"] = os.path.basename(card_path)

        if raw.get("screenshot_png"):
            png_path = os.path.join(settings.debug_dir, f"{base}.png")
            with open(png_path, "wb") as f:
                f.write(raw["screenshot_png"])
            files["png"] = os.path.basename(png_path)

        logger.debug("Сохранены debug-файлы: %s", files)
        return files

    # ------------------------------------------------------------------ #
    def get_card(self, url: str) -> dict:
        """Полный разбор: вернуть структурированную карточку + debug-файлы."""
        t0 = time.monotonic()
        logger.info("get_card: старт, url=%s", url)
        try:
            raw = self.repo.fetch_raw(url)
        except AntibotBlockedError as exc:
            self._emit_blocked(url, exc)
            raise
        card = build_card(raw["html"], raw["nuxt_state"], raw["url"])
        card_dict = card.model_dump()
        files = self._save_debug(self._basename(raw["url"]), raw, card_dict)
        took = round(time.monotonic() - t0, 2)
        emit_event("ozon.card.parsed",
                   {"url": raw["url"], "sku": card.sku, "took_s": took})
        logger.info("get_card: готово за %sс, sku=%s", took, card.sku)
        return {"card": card_dict, "debug_files": files or None}

    def get_raw(self, url: str) -> dict:
        """Только сырьё: вернуть __NUXT__ JSON + debug-файлы."""
        t0 = time.monotonic()
        logger.info("get_raw: старт, url=%s", url)
        try:
            raw = self.repo.fetch_raw(url)
        except AntibotBlockedError as exc:
            self._emit_blocked(url, exc)
            raise
        sku = OzonRepository.sku_from_url(raw["url"])
        files = self._save_debug(self._basename(raw["url"]), raw, None)
        took = round(time.monotonic() - t0, 2)
        emit_event("ozon.raw.parsed",
                   {"url": raw["url"], "sku": sku, "took_s": took})
        logger.info("get_raw: готово за %sс, sku=%s", took, sku)
        return {"sku": sku, "data": raw["nuxt_state"], "debug_files": files or None}

    # by-id обёртки
    def get_card_by_id(self, sku: str) -> dict:
        return self.get_card(OzonRepository.url_from_sku(sku))

    def get_raw_by_id(self, sku: str) -> dict:
        return self.get_raw(OzonRepository.url_from_sku(sku))

    # ------------------------------------------------------------------ #
    def _emit_blocked(self, url: str, exc: AntibotBlockedError) -> None:
        """
        Зафиксировать факт блокировки антиботом.

        Сейчас событие уходит в Kafka через emit_event (при KAFKA_ENABLED=false
        просто пишется в лог уровня WARNING и дальше не идёт — мягкая деградация).
        Когда брокер подключат, эти же события начнут собираться для анализа
        неслучайности пропусков (какие товары/когда чаще блокируются).
        """
        sku = OzonRepository.sku_from_url(url)
        logger.warning("Антибот заблокировал парсинг: url=%s sku=%s", url, sku)
        emit_event("ozon.blocked",
                   {"url": url, "sku": sku, "reason": str(exc)})