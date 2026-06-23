# -*- coding: utf-8 -*-
"""
card_parser.py — модуль для парсинга карточек товара Ozon.

Что делает:
  1. Принимает на вход URL карточки товара.
  2. Открывает её в headless-Chrome со stealth (та же логика, что и в parser.py —
     именно она проходит антибот Ozon).
  3. Достаёт встроенный объект window.__NUXT__.state из HTML.
  4. Сохраняет СЫРЫЕ данные о товаре в JSON-файл, структурированный через pprint
     (без преобразования полей — как ты и просила, чтобы посмотреть в исходном виде).

Запуск:
    python card_parser.py "https://www.ozon.ru/product/.../"

Переиспользует подход setup_driver() / close() из исходного parser.py.
"""

import os
import re
import sys
import json
import time
import random
import shutil
import logging
import tempfile
import pprint
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium_stealth import stealth
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType


# --- Логирование (как в parser.py, но пишем рядом с модулем, а не в /app/logs) ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Куда складывать результаты. Локально — папка ./output рядом с модулем.
OUTPUT_DIR = os.getenv("CARD_OUTPUT_DIR", "output")

# Запускать ли браузер невидимым (headless).
# ВНИМАНИЕ: в headless антибот срабатывает ЧАЩЕ. Видимое окно помогало обходить
# защиту. Если защита мешает — поставь False (окно появится), либо см. ниже про
# undetected-chromedriver.
HEADLESS = os.getenv("CARD_HEADLESS", "true").lower() == "true"


class OzonCardParser:
    """
    Парсер одной карточки товара.

    setup_driver() и close() намеренно повторяют логику из OzonSellerParser
    в исходном parser.py — это та самая stealth-конфигурация, которая
    проходит антибот Ozon. Остальное (RabbitMQ, CSV, прокси, пути /app)
    сюда не тащим: модуль самодостаточный и запускается локально.
    """

    def __init__(self):
        self.driver = None
        self.wait = None
        # Уникальная временная директория для профиля Chrome (как в оригинале)
        self.chrome_temp_dir = tempfile.mkdtemp()
        logging.info(f"Инициализация парсера карточек, профиль: {self.chrome_temp_dir}")

        os.makedirs(OUTPUT_DIR, exist_ok=True)

        try:
            self.setup_driver()
            self.wait = WebDriverWait(self.driver, 15)
        except Exception as e:
            logging.error(f"❌ Ошибка инициализации парсера: {e}", exc_info=True)
            self.close()
            raise

    # ------------------------------------------------------------------ #
    #  Драйвер: переиспользуем stealth-настройку из parser.py             #
    # ------------------------------------------------------------------ #
    def setup_driver(self):
        """Настройка Chrome со stealth. Логика взята из parser.py."""
        chrome_options = Options()

        if HEADLESS:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-setuid-sandbox")
        chrome_options.add_argument("--window-size=1920,1080")

        # Stealth-опции
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-features=UserAgentClientHint")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        ]
        chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")

        # Уникальный профиль
        chrome_options.add_argument(f"--user-data-dir={self.chrome_temp_dir}")

        try:
            service = Service(ChromeDriverManager(chrome_type=ChromeType.GOOGLE).install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)

            stealth(
                self.driver,
                languages=["ru-RU", "ru", "en-US", "en"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
                run_on_insecure_origins=False
            )
            logging.info("✅ Драйвер успешно инициализирован")
        except Exception as e:
            logging.error(f"❌ Ошибка создания драйвера: {e}", exc_info=True)
            raise

    # ------------------------------------------------------------------ #
    #  Получение HTML карточки                                           #
    # ------------------------------------------------------------------ #
    def random_mouse_movements(self):
        """Случайные движения мышью для имитации человека. Взято из parser.py."""
        try:
            window_size = self.driver.get_window_size()
            width = window_size['width']
            height = window_size['height']

            x1 = random.randint(100, width - 100)
            y1 = random.randint(100, height - 100)
            x2 = random.randint(100, width - 100)
            y2 = random.randint(100, height - 100)

            actions = webdriver.ActionChains(self.driver)
            actions.move_by_offset(x1, y1).pause(random.uniform(0.1, 0.3))
            actions.move_by_offset(x2 - x1, y2 - y1).pause(random.uniform(0.1, 0.3))
            actions.perform()

            scroll_pixels = random.randint(200, 800)
            self.driver.execute_script(f"window.scrollBy(0, {scroll_pixels});")
            time.sleep(random.uniform(0.5, 1.5))
        except Exception as e:
            logging.debug(f"⚠️ Ошибка при движении мышью: {e}")

    def check_and_handle_blocking(self) -> bool:
        """Проверка, не отдали ли нам капчу/блок. Маркеры взяты из parser.py."""
        blocking_indicators = [
            "//h1[contains(text(), 'Доступ ограничен')]",
            "//h1[contains(text(), 'Ой!')]",
            "//title[contains(text(), 'Доступ')]",
            "//div[contains(text(), 'проверку')]",
            "//div[contains(text(), 'безопасност')]",
            "//iframe[contains(@src, 'captcha')]",
            "//input[@name='captcha']",
        ]
        for indicator in blocking_indicators:
            try:
                if self.driver.find_elements(By.XPATH, indicator):
                    logging.warning(f"🛑 Обнаружена блокировка: {indicator}")
                    return True
            except Exception:
                continue
        return False

    def fetch_html(self, url: str) -> str:
        """Открыть карточку и вернуть HTML страницы (логика из load_seller_page)."""
        self.driver.set_page_load_timeout(30)
        time.sleep(random.uniform(2, 4))  # пауза ДО загрузки, как в оригинале

        logging.info(f"🌐 Открываем карточку: {url}")
        self.driver.get(url)

        # Сразу проверяем, не блок ли это.
        if self.check_and_handle_blocking():
            logging.warning("🛑 Похоже, антибот отдал капчу/блок. "
                            "Если запускаешь с HEADLESS=false — пройди проверку в окне руками, "
                            "потом данные дочитаются.")

        # Пауза + человеческое поведение: движения мыши и плавный скролл.
        time.sleep(random.uniform(2, 4))
        self.random_mouse_movements()
        self.random_mouse_movements()
        time.sleep(random.uniform(2, 4))

        # Ждём, пока в исходнике появится __NUXT__ — это есть и на карточке,
        # и на странице продавца. Признак, что Ozon отдал реальную страницу,
        # а не капчу. (Раньше ждали виджет карточки, но его нет у продавца.)
        try:
            self.wait.until(
                lambda d: "__NUXT__" in d.page_source
            )
            logging.info("✅ В странице появился __NUXT__ — похоже, отдалась реальная страница.")
        except Exception:
            logging.warning("⚠️ __NUXT__ так и не появился — возможно, антибот или редкая вёрстка. "
                            "Всё равно пробуем достать данные из того, что есть.")

        html = self.driver.page_source

        # Всегда сохраняем HTML и скриншот — чтобы посмотреть глазами, что пришло.
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_html = os.path.join(OUTPUT_DIR, f"debug_{ts}.html")
        debug_png = os.path.join(OUTPUT_DIR, f"debug_{ts}.png")
        try:
            with open(debug_html, "w", encoding="utf-8") as f:
                f.write(html)
            self.driver.save_screenshot(debug_png)
            logging.info(f"🧪 Для отладки сохранены: {debug_html} и {debug_png}")
        except Exception as e:
            logging.warning(f"⚠️ Не удалось сохранить отладочные файлы: {e}")

        return html

    # ------------------------------------------------------------------ #
    #  Извлечение window.__NUXT__.state                                 #
    # ------------------------------------------------------------------ #
    @staticmethod
    def extract_nuxt_state(html: str) -> dict:
        """
        Достаёт объект window.__NUXT__.state из HTML.

        В странице это выглядит так:
            window.__NUXT__.state = '....большая строка....';
        Причём содержимое — это JSON, завёрнутый в строку (отсюда двойное
        экранирование вида \\u002F). Поэтому:
            1) вырезаем содержимое одинарных кавычек после .state =
            2) json.loads первый раз — раскрывает строку и экранирование
            3) если на выходе снова строка (а не dict) — json.loads ещё раз.
        """
    @staticmethod
    def extract_nuxt_state(html: str) -> dict:
        """
        Достаёт объект window.__NUXT__.state из HTML.

        В странице это выглядит так:
            window.__NUXT__.state = '....большая строка....';
        Содержимое — JSON, завёрнутый в строковый литерал, поэтому внутри стоят
        экранированные последовательности (\\u002F вместо /, \\" и т.п.), а также
        могут встречаться апострофы внутри текста. Прошлый способ
        json.loads('"'+raw+'"') рвался на таких символах — поэтому теперь ищем
        границы строки вручную (с учётом экранирования) и аккуратно раскодируем.
        """
        marker = "window.__NUXT__.state"
        idx = html.find(marker)
        if idx == -1:
            has_nuxt = "__NUXT__" in html
            logging.error(f"❌ Маркер '{marker}' не найден. '__NUXT__' в HTML: {has_nuxt}. "
                          f"Длина HTML: {len(html)}.")
            raise ValueError(
                "Не нашли window.__NUXT__.state в HTML. "
                "Скорее всего, вместо карточки пришла капча/блок антибота. "
                f"(__NUXT__ в HTML: {'есть' if has_nuxt else 'НЕТ'}, длина HTML: {len(html)}). "
                "Открой debug_*.png в папке output."
            )

        logging.info(f"🔎 Маркер __NUXT__.state найден на позиции {idx}.")

        # Находим '=' после маркера, затем первую кавычку-ограничитель (' или ").
        eq = html.find("=", idx)
        p = eq + 1
        while p < len(html) and html[p] in " \t\r\n":
            p += 1
        quote = html[p]
        logging.info(f"🔎 Кавычка-ограничитель state: {quote!r} на позиции {p}.")
        if quote not in ("'", '"'):
            raise ValueError(f"Не нашли кавычку после 'state =', увидели: {html[p:p+30]!r}")

        # Идём от p+1 до закрывающей такой же кавычки, ПРОПУСКАЯ экранированные
        # символы (\\ + любой). Так апострофы внутри текста нас не собьют.
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
        logging.info(f"🔎 Длина сырого литерала state: {len(raw)} символов.")

        # Раскодируем тело строкового литерала в нормальную строку JSON.
        decoded = None
        try:
            decoded = raw.encode("utf-8").decode("unicode_escape").encode("latin-1").decode("utf-8")
            logging.info("🔎 Раскодирование через unicode_escape прошло успешно.")
        except (UnicodeDecodeError, UnicodeEncodeError) as e:
            logging.warning(f"⚠️ unicode_escape не сработал ({e}), пробую json.loads-обёртку.")
            try:
                decoded = json.loads(f'"{raw}"')
            except json.JSONDecodeError as e2:
                OzonCardParser._log_json_error_context(raw, e2)
                raise

        # Теперь decoded — строка с JSON. Разбираем в dict.
        try:
            data = json.loads(decoded) if isinstance(decoded, str) else decoded
        except json.JSONDecodeError as e:
            OzonCardParser._log_json_error_context(decoded, e)
            # Сохраняем сырой литерал и декодированную строку — чтобы посмотреть
            # глазами, какой символ ломает разбор (особенно вокруг позиции ошибки).
            try:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                with open(os.path.join(OUTPUT_DIR, f"nuxt_raw_{ts}.txt"), "w", encoding="utf-8") as fr:
                    fr.write(raw)
                if isinstance(decoded, str):
                    with open(os.path.join(OUTPUT_DIR, f"nuxt_decoded_{ts}.txt"), "w", encoding="utf-8") as fd:
                        fd.write(decoded)
                logging.error(f"❌ Сохранил nuxt_raw_{ts}.txt и nuxt_decoded_{ts}.txt в output "
                              f"для разбора проблемного места.")
            except Exception as save_err:
                logging.warning(f"⚠️ Не смог сохранить дамп для отладки: {save_err}")
            raise

        logging.info(f"✅ __NUXT__.state разобран. Ключей верхнего уровня: "
                     f"{list(data.keys()) if isinstance(data, dict) else type(data).__name__}")
        return data

    @staticmethod
    def _log_json_error_context(text: str, err: json.JSONDecodeError):
        """Подробно логируем, что именно не так с JSON — окрестность позиции ошибки."""
        pos = getattr(err, "pos", None)
        logging.error(f"❌ Ошибка разбора JSON: {err}")
        if isinstance(text, str) and pos is not None:
            lo = max(0, pos - 60)
            hi = min(len(text), pos + 60)
            snippet = text[lo:hi]
            caret_at = pos - lo
            logging.error(f"❌ Контекст вокруг позиции {pos}:")
            logging.error(f"    ...{snippet}...")
            logging.error(f"    {' ' * (caret_at + 3)}^ здесь")
            logging.error(f"❌ Символ в позиции {pos}: {text[pos]!r} (код {ord(text[pos])})")

    # ------------------------------------------------------------------ #
    #  Главный метод: url -> файл с сырым JSON                           #
    # ------------------------------------------------------------------ #
    @staticmethod
    def extract_sku(url: str) -> str:
        """
        Достаёт артикул (sku) товара из URL карточки Ozon.
        Если не нашёлся (нестандартная ссылка/страница продавца) — берёт
        последний кусок пути, иначе возвращает 'unknown'.
        """
        sku_match = re.search(r"-(\d+)/?(?:\?|$)", url)
        if sku_match:
            return sku_match.group(1)
        slug = re.findall(r"/([^/?]+)", url)
        return slug[-1] if slug else "unknown"

    @staticmethod
    def build_basename(url: str) -> str:
        """
        Базовое имя файлов вида:  ozon_<sku>_<ГГГГММДД_ЧЧММСС>
        Маркетплейс в префиксе — чтобы не путать с будущими площадками,
        таймстамп — чтобы повторные прогоны одной карточки не перезаписывались.
        """
        sku = OzonCardParser.extract_sku(url)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"ozon_{sku}_{ts}"

    def parse_card(self, url: str) -> str:
        """
        Полный цикл по одной карточке:
            URL -> HTML -> __NUXT__.state -> файл .json (сырой, структурирован pprint).
        Возвращает путь к сохранённому файлу.
        """
        html = self.fetch_html(url)
        data = self.extract_nuxt_state(html)

        base = self.build_basename(url)
        out_path = os.path.join(OUTPUT_DIR, f"{base}.json")

        # Сохраняем СЫРЫЕ данные, структурируя через pprint.
        # pprint раскладывает вложенный словарь по строкам с отступами —
        # удобно читать глазами. width пошире, чтобы строки не рвались слишком часто.
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(pprint.pformat(data, width=120, sort_dicts=False))

        logging.info(f"✅ Сырые данные карточки сохранены: {out_path}")
        return out_path

    def parse_card_full(self, url: str) -> dict:
        """
        Расширенный разбор для веб-сервиса.

        Делает то же, что parse_card, но:
          - сохраняет ПОЛНЫЙ html страницы (не только debug-копию),
          - сохраняет json с данными товара,
          - возвращает словарь с самими данными и путями к файлам,
            чтобы сервис мог отдать JSON в ответе и сослаться на файлы.
        """
        html = self.fetch_html(url)
        data = self.extract_nuxt_state(html)

        base = self.build_basename(url)        # ozon_<sku>_<timestamp>
        sku = self.extract_sku(url)

        json_path = os.path.join(OUTPUT_DIR, f"{base}.json")
        html_path = os.path.join(OUTPUT_DIR, f"{base}.html")

        # Полный HTML страницы — чтобы можно было посмотреть целиком.
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        # JSON с данными товара. Здесь — настоящий JSON (а не pprint),
        # т.к. его удобнее и отдавать в ответе, и читать программно.
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # Структурированная карточка: вытаскиваем нужные поля из HTML-виджетов и __NUXT__.
        card = None
        card_path = None
        try:
            from ozon_transform import build_card
            card = build_card(html, data, url).model_dump()
            card_path = os.path.join(OUTPUT_DIR, f"{base}_card.json")
            with open(card_path, "w", encoding="utf-8") as f:
                json.dump(card, f, ensure_ascii=False, indent=2)
            logging.info(f"✅ Структурированная карточка сохранена: {card_path}")
        except Exception as e:
            logging.error(f"⚠️ Не удалось собрать карточку: {e}", exc_info=True)

        logging.info(f"✅ Сохранены: {json_path} и {html_path}")
        return {
            "tag": sku,
            "json_path": json_path,
            "html_path": html_path,
            "card_path": card_path,
            "data": data,
            "card": card,
        }

    # ------------------------------------------------------------------ #
    #  Закрытие: логика close() из parser.py                            #
    # ------------------------------------------------------------------ #
    def close(self):
        """Корректное закрытие драйвера и очистка временной папки (как в parser.py)."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logging.error(f"❌ Ошибка при закрытии драйвера: {e}")
            self.driver = None

        if self.chrome_temp_dir and os.path.exists(self.chrome_temp_dir):
            try:
                shutil.rmtree(self.chrome_temp_dir)
            except Exception as e:
                logging.warning(f"⚠️ Не удалось удалить временную директорию: {e}")


def main():
    # Откуда брать URL, по приоритету:
    #   1) аргумент командной строки:  python card_parser.py "https://..."
    #   2) переменная окружения CARD_URL (используется в Docker, там нет input)
    #   3) интерактивный ввод в консоли (удобно для запуска Play в PyCharm)
    if len(sys.argv) >= 2:
        url = sys.argv[1].strip()
    elif os.getenv("CARD_URL"):
        url = os.getenv("CARD_URL").strip()
    else:
        url = input("Введите URL карточки Ozon: ").strip()

    if not url:
        print("URL не введён. Завершаюсь.")
        sys.exit(1)

    parser = None
    try:
        parser = OzonCardParser()
        out_path = parser.parse_card(url)
        print(f"\nГотово. Сырой JSON здесь: {out_path}")
    except Exception as e:
        logging.error(f"❌ Не удалось распарсить карточку: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if parser:
            parser.close()


if __name__ == "__main__":
    main()
