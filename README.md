# Bible Bot

Telegram-бот присылает каждый день один отобранный стих или короткий отрывок
из Нового Завета в Синодальном переводе. Пользователь выбирает время и часовой
пояс; после завершения цикла бот показывает итог и предлагает новый круг,
последовательное чтение или тематическую подборку.

## Сценарий пользователя

1. `/start` показывает приветствие и предлагает быстрое начало или настройку.
2. Пользователь выбирает время и часовой пояс.
3. Первый стих приходит сразу, плановая рассылка начинается на следующий день.
4. Под стихом доступны контекст, сохранение и настройки.
5. После последнего дня бот присылает Откровение 22:21, показывает число
   сохранённых стихов и ставит рассылку на паузу.

Основной цикл содержит 365 уникальных отправок. В общем режиме стих дня один
для всех, но приходит в локальное время пользователя. Доступны темы веры,
надежды, любви, молитвы, слов Иисуса, утешения и отношений с людьми.

## Архитектура на Vercel

```text
Telegram webhook ─┐
                  ├─> FastAPI на Vercel ─> Neon Postgres
QStash / Cron ────┘             └────────> Telegram Bot API
```

- `POST /api/telegram` принимает защищённые Telegram webhook-обновления.
- `POST /api/cron` ищет пользователей, чьё локальное время отправки наступило.
- Neon хранит пользователей, расписания, избранное, прогресс и защиту от
  повторных webhook/отправок.
- QStash вызывает delivery endpoint раз в две минуты. На Vercel Pro вместо
  него можно использовать Vercel Cron раз в минуту.
- Текст Нового Завета лежит в репозитории; внешний библейский API не нужен.

SQLite и long polling оставлены только для локальной разработки. Docker для
Vercel не используется.

## Деплой

### 1. Neon

Создайте проект в Neon и скопируйте **pooled connection string** — в имени
хоста должен быть суффикс `-pooler`. Это значение переменной `DATABASE_URL`.

Вручную загружать SQL необязательно: приложение выполняет безопасные
`CREATE TABLE IF NOT EXISTS` при первом рабочем запросе. Если хочется создать
и проверить таблицы заранее, выполните [sql/schema.sql](sql/schema.sql) в Neon
SQL Editor.

### 2. Vercel

Импортируйте GitHub-репозиторий в Vercel как обычный Python-проект. Корневой
`app.py` — ASGI/FastAPI entrypoint, Python зафиксирован в `.python-version`.

Добавьте Production environment variables:

```dotenv
BOT_TOKEN=...
DATABASE_URL=postgresql://...-pooler.../neondb?sslmode=require
TELEGRAM_WEBHOOK_SECRET=...
CRON_SECRET=...
DEFAULT_TIME=09:00
DEFAULT_TIMEZONE=Europe/Minsk
LOG_LEVEL=INFO
```

Сгенерируйте два разных секрета:

```bash
python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

После деплоя откройте `https://<project>.vercel.app/api/health`. Все три поля
`*_configured` должны быть `true`.

### 3. Telegram webhook

На локальной машине задайте те же `BOT_TOKEN` и
`TELEGRAM_WEBHOOK_SECRET`, затем выполните:

```bash
export APP_URL=https://<project>.vercel.app
python scripts/configure_telegram.py
```

Скрипт устанавливает webhook с секретным заголовком и регистрирует команды
бота.

### 4. Запуск ежедневной доставки

Для Vercel Hobby удобно использовать QStash. Создайте аккаунт Upstash, возьмите
`QSTASH_TOKEN` и выполните:

```bash
export APP_URL=https://<project>.vercel.app
export QSTASH_TOKEN=...
export CRON_SECRET=...
python scripts/configure_qstash.py
```

Скрипт создаёт расписание `*/2 * * * *` и передаёт `CRON_SECRET` в защищённый
endpoint. Это 720 вызовов в сутки.

На Vercel Pro можно обойтись без QStash: скопируйте
`vercel.pro.json.example` в `vercel.json`, задеплойте ещё раз и оставьте
`CRON_SECRET` в переменных Vercel. Встроенный cron будет работать каждую
минуту.

## Локальный запуск

Нужны Python 3.12 и токен от [@BotFather](https://t.me/BotFather).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
export BOT_TOKEN=...
python -m bible_bot
```

Если `DATABASE_URL` не задан, создаётся SQLite-файл
`runtime/bible_bot.db`. Локальный процесс использует long polling и собственный
планировщик.

## Команды

- `/today` — сегодняшний стих;
- `/settings` — время, часовой пояс и состояние рассылки;
- `/favorites` — сохранённые стихи;
- `/pause` — пауза;
- `/help` — справка.

## Надёжность доставки

- Следующее время хранится в UTC, а расписание рассчитывается по IANA-зоне
  пользователя (`Europe/Minsk`, а не фиксированному `UTC+3`).
- Уникальная запись `(chat_id, local_date, kind)` не позволяет cron отправить
  дневной стих повторно.
- Распределённая блокировка с автоматическим сроком жизни не даёт двум
  инстансам Vercel одновременно обрабатывать очередь.
- Telegram `update_id` сохраняется в БД, поэтому повтор webhook не повторяет
  нажатие пользователя.
- Ввод произвольного времени и зоны хранится в Neon и переживает холодный
  запуск Vercel.
- При rate limit повтор учитывает `retry_after`; временная ошибка откладывает
  пользователя на 10 минут; блокировка бота отключает подписку.

## Структура

```text
app.py                       FastAPI entrypoint для Vercel
bible_bot/
  app.py                     локальный long polling
  vercel_app.py              webhook и cron API
  handlers.py                онбординг, настройки, избранное и циклы
  scheduler.py               ежедневная доставка
  database.py                SQLite и выбор backend
  postgres_database.py       Neon/Postgres backend
  content.py                 чтение корпуса и выбор отрывков
  data/                      локальный Новый Завет и планы
scripts/
  configure_telegram.py      установка webhook и команд
  configure_qstash.py        создание расписания QStash
sql/schema.sql               схема Neon для ручного запуска
tests/
```

## Проверка

```bash
ruff check .
pytest
```

Источник корпуса и условия использования описаны в
[NOTICE.md](NOTICE.md). Исходный набор помечает Синодальный перевод как Public
Domain.
