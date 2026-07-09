# -*- coding: utf-8 -*-
"""
kafka_config.py — настройки Kafka-интеграции (топики, регион, consumer group).

Топики: <поток>.<tasks|results>.<geo_code>. Сейчас один регион — spb.
При добавлении региона поднимается воркер с другим OZON_GEO_CODE.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class KafkaWorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bootstrap_servers: str = Field(default="localhost:9092", alias="KAFKA_BOOTSTRAP_SERVERS")
    geo_code: str = Field(default="spb", alias="OZON_GEO_CODE")
    geo_name: str = Field(default="Санкт-Петербург", alias="OZON_GEO_NAME")
    group_id: str = Field(default="ozon-parser-spb", alias="KAFKA_GROUP_ID")
    poll_timeout_ms: int = Field(default=1000, alias="KAFKA_POLL_TIMEOUT_MS")
    reconnect_delay_s: int = Field(default=5, alias="KAFKA_RECONNECT_DELAY_S")

    @property
    def select_tasks_topic(self) -> str:
        return f"select.tasks.{self.geo_code}"

    @property
    def select_results_topic(self) -> str:
        return f"select.results.{self.geo_code}"

    @property
    def parse_tasks_topic(self) -> str:
        return f"parse.tasks.{self.geo_code}"

    @property
    def parse_results_topic(self) -> str:
        return f"parse.results.{self.geo_code}"

    @property
    def task_topics(self) -> list[str]:
        return [self.select_tasks_topic, self.parse_tasks_topic]


kafka_worker_settings = KafkaWorkerSettings()