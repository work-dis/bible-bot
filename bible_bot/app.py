from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from bible_bot.config import Settings
from bible_bot.content import BibleCatalog
from bible_bot.database import Database
from bible_bot.handlers import create_router
from bible_bot.scheduler import DailyScheduler


async def main() -> None:
    settings = Settings.from_env()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    database = Database(settings.database_location)
    await database.connect()
    anchor_today = datetime.now(ZoneInfo(settings.default_timezone)).date()
    anchor_date = await database.get_or_create_plan_anchor(anchor_today)
    catalog = BibleCatalog.from_data_dir(settings.data_dir)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(create_router(database, catalog, settings, anchor_date))

    scheduler = DailyScheduler(
        bot=bot,
        database=database,
        catalog=catalog,
        anchor_date=anchor_date,
        poll_seconds=settings.scheduler_poll_seconds,
    )
    scheduler_task = asyncio.create_task(scheduler.run(), name="daily-chapter-scheduler")

    await bot.set_my_commands(
        [
            BotCommand(command="today", description="Получить сегодняшнюю главу"),
            BotCommand(command="settings", description="Настройки рассылки"),
            BotCommand(command="channel", description="Открыть публичный канал"),
            BotCommand(command="favorites", description="Сохранённые главы"),
            BotCommand(command="pause", description="Приостановить рассылку"),
            BotCommand(command="help", description="Справка"),
        ]
    )

    try:
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        scheduler.stop()
        scheduler_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await scheduler_task
        await dispatcher.storage.close()
        await bot.session.close()
        await database.close()


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
