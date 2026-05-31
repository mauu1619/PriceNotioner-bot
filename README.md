# Pars Bot

Современный асинхронный Telegram-бот для отслеживания цен на товары маркетплейсов (реализована поддержка Wildberries). Бот написан на базе aiogram 3, использует PostgreSQL для хранения данных, Redis в качестве брокера задач и Taskiq для периодического фонового мониторинга цен.

## 🏗 Архитектура проекта

Приложение состоит из 5 основных контейнеров/сервисов:

1.  **Бот (Backend):** Обрабатывает команды от пользователей, ведет FSM диалоги (добавление товаров), присылает меню и проводит оплату через Telegram Stars.
2.  **База данных (PostgreSQL):** Хранит пользователей, тарифы (Free/Pro), товары и лог платежей.
3.  **Брокер сообщений (Redis):** Используется для управления фоновыми задачами Taskiq.
4.  **Worker (Taskiq):** Отдельный процесс, который в фоне асинхронно опрашивает API маркетплейсов для списка товаров. Если цена падает ниже установленной, он формирует уведомление и отправляет его в Telegram.
5.  **Scheduler (Taskiq Beat):** Крон-планировщик, который раз в минуту подает Worker'у команду начать обход базы.

## 🛠 Стек технологий

- **Язык:** Python 3.12
- **Управление зависимостями:** [uv](https://github.com/astral-sh/uv)
- **Бот API:** [aiogram 3](https://docs.aiogram.dev/)
- **База данных:** PostgreSQL + [asyncpg](https://github.com/MagicStack/asyncpg)
- **ORM:** [SQLModel](https://sqlmodel.tiangolo.com/) (обертка над SQLAlchemy и Pydantic)
- **Миграции БД:** [Alembic](https://alembic.sqlalchemy.org/)
- **Фоновые задачи:** [Taskiq](https://taskiq-python.github.io/) + Redis
- **Парсинг:** `curl_cffi` (имитация отпечатка браузера Chrome для обхода блокировок) + SOCKS5 прокси.
- **Логирование:** [loguru](https://github.com/Delgan/loguru) (с поддержкой структурированного JSON формата).

## 🗄 Схема базы данных

Архитектура базы данных (`src/db/models/models.py`) состоит из следующих таблиц:

- **Plan:** Описание тарифов (`id`, `name`, `stars_price`, `max_products`, `check_interval_minutes`). Базовые тарифы: `Free` и `Pro`.
- **User:** Пользователи бота (`id` - Telegram ID, `username`, `plan_id` - FK на Plan, дата создания, дата окончания подписки).
- **Product:** Отслеживаемые товары (`id`, `user_id`, `url`, `title`, `current_price`, `target_price`, время последнего чека).
- **Payment:** Лог платежей через Telegram Stars (`id`, `user_id`, `telegram_payment_charge_id`, сумма XTR, статус транзакции).

## 🚀 Инструкция по запуску

Проект полностью контейнеризирован и запускается одной командой.

### 1. Подготовка

Склонируйте репозиторий и создайте файл с переменными окружения из шаблона:

```bash
cp .env.example .env
```

Отредактируйте файл `.env`:

- `BOT_TOKEN`: Укажите токен вашего бота от [@BotFather](https://t.me/BotFather).
- `ADMIN_IDS`: ID администраторов через запятую (для доступа к `/admin`).
- `PROXY_URL`: SOCKS5 или HTTP прокси для работы бота.
- `USE_PROXY_FOR_PARSER`: `false`, если хотите парсить Wildberries напрямую (рекомендуется, если сервер в РФ), или `true`, если через прокси.
- `LOG_FORMAT`: `text` для красивого вывода в консоль, `json` для продакшена.

### 2. Запуск через Docker Compose

Убедитесь, что у вас установлены Docker и Docker Compose. Выполните:

```bash
docker compose up -d --build
```

**Что произойдет при запуске:**

1.  Поднимутся базы данных PostgreSQL и Redis.
2.  Контейнер `bot` подождет базу, накатит миграции (`alembic upgrade head`), создаст дефолтные тарифы в БД (`src/db/seed.py`) и запустит aiogram.
3.  Поднимутся `worker` и `scheduler` от Taskiq, которые сразу начнут фоновый мониторинг цен.

### 3. Локальная разработка (без Docker для бота)

Если вы хотите запустить сервисы локально на своей машине:

#### Вариант А: Стандартный (через pip)

1.  Создайте виртуальное окружение и активируйте его:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # Для Linux/macOS
    # или
    .venv\Scripts\activate     # Для Windows
    ```
2.  Установите зависимости:
    ```bash
    pip install -r requirements.txt
    ```

#### Вариант Б: Современный (через uv)

1.  Установите зависимости:
    ```bash
    uv sync
    ```

#### Запуск сервисов:

1.  Поднимите только базы данных (если они не установлены локально):
    ```bash
    docker compose up -d db redis
    ```
2.  Примените миграции и создайте начальные данные:

    ```bash
    # Через pip:
    alembic upgrade head
    python3 -m src.db.seed

    # Через uv:
    uv run alembic upgrade head
    uv run python -m src.db.seed
    ```

3.  Запустите бота в первом терминале:

    ```bash
    # Через pip:
    python3 -m src.main

    # Через uv:
    uv run python -m src.main
    ```

4.  Запустите воркер во втором терминале:

    ```bash
    # Через pip:
    taskiq worker src.tasks.broker:broker src.tasks.price_check

    # Через uv:
    uv run taskiq worker src.tasks.broker:broker src.tasks.price_check
    ```

5.  Запустите планировщик в третьем терминале:

    ```bash
    # Через pip:
    taskiq scheduler src.tasks.broker:scheduler src.tasks.price_check

    # Через uv:
    uv run taskiq scheduler src.tasks.broker:scheduler src.tasks.price_check
    ```

## 📝 Основные команды бота

- `/start` - Приветствие, регистрация пользователя (автоматически присваивается тариф Free). Вызов главного меню.
- `/admin` - Админ-панель (доступна только ID из списка `ADMIN_IDS`). Позволяет смотреть статистику, делать рассылку и выдавать PRO-подписки.
- **Меню: Добавить товар** - FSM-состояние для добавления ссылки (или артикула) на товар Wildberries. Бот парсит товар, сообщает текущую цену и просит указать желаемую цену.
- **Меню: Мои товары** - Список всех ваших товаров с возможностью изменить цель или удалить.
- **Меню: Мой профиль** - Просмотр текущего тарифа и лимитов. Возможность купить PRO за Telegram Stars.
- **Меню: Баланс Stars** - Информационная вкладка о внутренней валюте.
