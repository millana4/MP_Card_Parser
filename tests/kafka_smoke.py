# -*- coding: utf-8 -*-
"""
kafka_smoke.py — проверка живой связи с Kafka (эхо-тест).

Кладёт тестовую задачу в топик задач, ждёт результат в топике результатов,
сверяет эхо-поля. Проверяет всю цепочку: брокер ↔ воркер ↔ результат.

Требует РАБОТАЮЩЕГО брокера и ЗАПУЩЕННОГО воркера.

Запуск (на сервере, где доступен брокер):
    python scripts/kafka_smoke.py --broker <ip:port> --geo spb --flow parse
    python scripts/kafka_smoke.py --broker <ip:port> --geo spb --flow select

По умолчанию flow=parse (быстрее — одна карточка). Для select парсер зайдёт
в несколько карточек, это дольше.
"""

import argparse
import json
import uuid
import time
import sys

from kafka import KafkaProducer, KafkaConsumer


def make_parse_task():
    task_id = str(uuid.uuid4())
    card_id = str(uuid.uuid4())
    task = {
        "task_id": task_id,
        "card_id": card_id,
        "sku": "4163755961",          # подставьте реальный существующий sku
        "geo": "Санкт-Петербург",
    }
    return task, task_id


def make_select_task():
    task_id = str(uuid.uuid4())
    task = {
        "task_id": task_id,
        "set_id": str(uuid.uuid4()),
        "stratum_id": str(uuid.uuid4()),
        "geo": "Санкт-Петербург",
        "query": "Рубашка женская",
        "count": 2,
        "is_seasonal": False,
        "exclude": [],
    }
    return task, task_id


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--broker", required=True, help="адрес брокера, напр. 10.0.0.5:9092")
    ap.add_argument("--geo", default="spb", help="код региона (суффикс топиков)")
    ap.add_argument("--flow", choices=["parse", "select"], default="parse")
    ap.add_argument("--timeout", type=int, default=180,
                    help="сколько секунд ждать результат (парсинг карточки ~12с)")
    args = ap.parse_args()

    tasks_topic = f"{args.flow}.tasks.{args.geo}"
    results_topic = f"{args.flow}.results.{args.geo}"

    if args.flow == "parse":
        task, task_id = make_parse_task()
    else:
        task, task_id = make_select_task()

    print(f"Брокер:          {args.broker}")
    print(f"Топик задач:     {tasks_topic}")
    print(f"Топик результата:{results_topic}")
    print(f"task_id:         {task_id}")
    print("-" * 50)

    # --- подписываемся на результаты ДО отправки, чтобы не пропустить ---
    consumer = KafkaConsumer(
        results_topic,
        bootstrap_servers=args.broker,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="latest",   # только новые результаты
        consumer_timeout_ms=1000,     # чтобы цикл ниже не блокировался навсегда
        group_id=f"smoke-{uuid.uuid4()}",  # уникальная группа — читаем сами
    )
    # дать консьюмеру подключиться и получить назначение партиций
    consumer.poll(timeout_ms=2000)

    # --- кладём задачу ---
    producer = KafkaProducer(
        bootstrap_servers=args.broker,
        value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
        acks="all",
    )
    producer.send(tasks_topic, value=task).get(timeout=30)
    producer.flush()
    print(f"Задача отправлена в {tasks_topic}, жду результат (до {args.timeout}с)...")

    # --- ждём результат с нашим task_id ---
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        batch = consumer.poll(timeout_ms=1000)
        for _, messages in batch.items():
            for msg in messages:
                result = msg.value
                if result.get("task_id") != task_id:
                    continue   # чужой результат — пропускаем
                print("-" * 50)
                print("ПОЛУЧЕН РЕЗУЛЬТАТ:")
                print(json.dumps(result, ensure_ascii=False, indent=2)[:800])
                print("-" * 50)
                _check(args.flow, task, result)
                consumer.close()
                producer.close()
                return
    print(f"ТАЙМАУТ: результат с task_id={task_id} не пришёл за {args.timeout}с")
    print("Проверьте: воркер запущен? подписан на этот регion? брокер тот же?")
    consumer.close()
    producer.close()
    sys.exit(1)


def _check(flow, task, result):
    """Сверка эхо-полей и базовой структуры."""
    ok = True

    def field(name, expected):
        nonlocal ok
        actual = result.get(name)
        match = actual == expected
        ok = ok and match
        print(f"  {'✓' if match else '✗'} {name}: {actual!r}"
              + ("" if match else f" (ожидалось {expected!r})"))

    # эхо-поля, общие
    field("task_id", task["task_id"])
    field("geo", task["geo"])

    if flow == "parse":
        field("card_id", task["card_id"])
        field("sku", task["sku"])
        print(f"  ok={result.get('ok')} | card={'есть' if result.get('card') else 'null'}"
              f" | error={result.get('error')}")
    else:
        field("set_id", task["set_id"])
        field("stratum_id", task["stratum_id"])
        print(f"  ok={result.get('ok')} | requested={result.get('requested_count')}"
              f" found={result.get('found_count')} | error={result.get('error')}")

    print("-" * 50)
    print("ИТОГ:", "ЭХО-ПОЛЯ СОВПАЛИ ✓" if ok else "РАСХОЖДЕНИЕ В ЭХО-ПОЛЯХ ✗")


if __name__ == "__main__":
    main()