# Marketplace Card Parser

Сервис парсинга карточек маркетплейсов. На вход — URL или артикул, на выход —
распарсенные данные (очищенная карточка или сырой JSON `__NUXT__`).

Сейчас поддержан Ozon. WB и Яндекс.Маркет добавляются как отдельные модули
внутри `app/marketplaces/`.

## Структура

```
app/
├── main.py                  # точка входа FastAPI
├── api/
│   ├── dependencies.py      # проверка ключа между сервисами (сейчас заглушка)
│   └── routes/              # ozon.py, files.py, health.py
├── core/
│   ├── config.py            # настройки + политики таймаутов/ретраев per-маркетплейс
│   ├── logging.py           # уровни логирования
│   ├── exceptions.py        # доменные ошибки (антибот / не найдено / невалидный вход)
│   └── security.py          # декодирование токена (заглушка)
├── marketplaces/ozon/
│   ├── parser.py            # Selenium + stealth: открыть страницу, получить HTML
│   ├── nuxt.py              # извлечение __NUXT__ (чистая функция, тестируемая)
│   ├── repository.py        # источник данных: url/id -> сырьё
│   ├── mapper.py            # сырьё -> доменная карточка OzonCard
│   ├── service.py           # оркестрация + сохранение debug-файлов + Kafka
│   ├── models.py            # доменные модели
│   └── schemas.py           # схемы API (запрос/ответ)
├── shared/kafka_logger.py   # журнал событий (мягкая деградация без брокера)
└── debug/                   # debug-артефакты (только при DEBUG=true)
tests/                       # тесты маппера на сохранённом HTML (без сети)
```

## Запуск в Docker

```bash
docker compose up --build
```

Swagger: http://localhost:8010/docs

Эндпоинты Ozon:
1. `POST /api/v1/ozon/card/by-id`
2. `POST /api/v1/ozon/card/by-url`
3. `POST /api/v1/ozon/raw/by-id`
4. `POST /api/v1/ozon/raw/by-url`

Ниже — файлы (debug) и служебные:
`GET /api/v1/files`, `GET /api/v1/files/{name}`, `GET /api/v1/health`, `GET /api/v1/health/ready`.

## Локальный запуск

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.main          # или: uvicorn app.main:app --port 8000
```

Локально Chrome работает headless и его чаще ловит антибот — для реального
парсинга используйте Docker (там Xvfb).

## Тесты

```bash
python -m pytest tests/ -v
```

Тесты гоняют маппер на сохранённом HTML из `tests/fixtures/` — без обращения
к Ozon. Меняя логику извлечения, сразу видно, не сломалось ли что-то.

## Debug-файлы

При `DEBUG=true` каждый запрос сохраняет в `app/debug/`: полный HTML, сырой
JSON, JSON карточки и скриншот. Имя — `ozon_<sku>_<ГГГГММДД_ЧЧММСС>`.
В проде ставьте `DEBUG=false` — файлы не пишутся, файловые эндпоинты пусты.

Очистить:
```bash
sudo rm -rf app/debug/*    # если файлы созданы из контейнера (root)
```

## Настройки (.env)

Скопируйте `.env.example` в `.env`. Ключевое:

| Переменная | Зачем |
|---|---|
| `DEBUG` | сохранять ли html/json/png и отдавать файловые эндпоинты |
| `LOG_LEVEL` | DEBUG / INFO / WARNING / ERROR |
| `KAFKA_ENABLED` | слать ли события в Kafka (без брокера сервис работает) |
| `OZON_RETRIES`, `OZON_*_TIMEOUT`, `OZON_PAUSE_*`, `OZON_RETRY_PAUSE_*` | политика Ozon: таймауты, паузы, ретраи (у каждого маркетплейса своя) |

## Авторизация и Kafka

`api/dependencies.py` — проверка межсервисного ключа, сейчас заглушка
(пропускает всё), прод-вариант закомментирован рядом.

Kafka — журнал событий для других сервисов (аналитика, таск-менеджер).
Не жёсткая зависимость: при выключенной/недоступной Kafka сервис парсит как обычно.
```
