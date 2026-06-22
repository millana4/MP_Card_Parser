FROM python:3.13-slim

# --- Системные зависимости (как в рабочем образе парсера продавцов) ---
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    xvfb \
    unzip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# --- Google Chrome ---
RUN mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /etc/apt/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/output

# Сервис не в headless: Chrome работает через виртуальный экран Xvfb,
# который поднимает entrypoint.sh (так же, как у работавшего parser.py).
# uvicorn запускается основным процессом — его логи видны в `docker compose logs`.
ENV CARD_HEADLESS=false
ENV CARD_OUTPUT_DIR=/app/output
ENV DISPLAY=:99
EXPOSE 8000

RUN chmod +x /app/entrypoint.sh
CMD ["/app/entrypoint.sh"]
