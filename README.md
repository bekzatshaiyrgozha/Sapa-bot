# Sapa Slaid Bot

Минимальная реализация Telegram-бота для управления недельными планами и проверки презентаций через OpenAI.

Кратко:
- Python 3.11+
- python-telegram-bot v20+ (async)
- SQLAlchemy (по умолчанию sqlite, можно использовать PostgreSQL через `DATABASE_URL`)
- OpenAI для проверки слайдов

Запуск локально (быстрый старт):

1. Создайте venv и установите зависимости (скрипт делает это автоматически):

```bash
./scripts/bootstrap_venv.sh
source .venv311/bin/activate
```

2. Настройте переменные окружения (или используйте `.env`):

```bash
# пример (или заполните .env)
export BOT_TOKEN="<ваш токен>"
export OPENAI_API_KEY="<ваш openai key>"
export DATABASE_URL="postgresql+asyncpg://postgres:SapaBotSlide2026@127.0.0.1:5433/sapa_bot_slide"
```

3. Запустите Postgres (docker-compose):

```bash
docker-compose up -d db
docker-compose logs -f db
```

4. Запуск бота локально:

```bash
set -a; source .env; set +a
python -m bot.main
```

Альтернатива — запустить бот внутри Docker (соберёт образ):

```bash
docker-compose up --build bot
```

Удобные команды в `Makefile`:
- `make bootstrap` — создать venv и установить зависимости
- `make start-db` — поднять Postgres
- `make run` — запустить бота локально (предварительно активировать venv)
- `make docker-run` — поднять сервисы через docker-compose

Файлы:
- `bot/main.py` — входная точка
- `bot/config.py` — конфиги
- `bot/db/` — модели и инициализация БД
- `bot/handlers/` — обработчики команд
- `bot/utils/slide_parser.py` — парсер pptx/pdf
- `bot/services/ai_checker.py` — вызов OpenAI и разбор JSON
- `bot/services/scheduler.py` — планировщик дедлайнов (APScheduler)

Дальше: добавить CRUD-обработчики для `admin`/`bm`, улучшить связь моделей, добавить миграции Alembic, тесты и CI.
