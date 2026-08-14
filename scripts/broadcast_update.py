from __future__ import annotations

import argparse
import asyncio
import os

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError, TelegramRetryAfter

from bible_bot.database import Database

CAMPAIGN = "bot-update-feedback-2026-08"
UPDATE_TEXT = (
    "🌿 <b>Бот обновился</b>\n\n"
    "Теперь здесь можно:\n"
    "• получать ежедневную главу Нового Завета;\n"
    "• выделять стихи и сохранять главы;\n"
    "• публиковать размышления в общем канале;\n"
    "• отправлять отзывы и предложения прямо через бота.\n\n"
    "Чтобы открыть обновлённое меню, отправьте /start."
)


async def send_with_rate_limit(bot: Bot, chat_id: int) -> str:
    while True:
        try:
            await bot.send_message(chat_id, UPDATE_TEXT)
            return "sent"
        except TelegramRetryAfter as exc:
            await asyncio.sleep(float(exc.retry_after) + 0.2)
        except TelegramForbiddenError:
            return "blocked"


async def broadcast(*, limit: int | None, dry_run: bool) -> int:
    token = os.getenv("BOT_TOKEN", "").strip()
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not token or not database_url:
        raise SystemExit("BOT_TOKEN and DATABASE_URL are required")

    database = Database(database_url)
    await database.connect()
    bot: Bot | None = None
    try:
        recipients = await database.list_broadcast_recipients(CAMPAIGN, limit=limit)
        print(f"Recipients pending for {CAMPAIGN}: {len(recipients)}")
        if dry_run:
            print("\nMessage preview:\n")
            print(UPDATE_TEXT)
            return 0

        bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        sent = blocked = failed = 0
        for chat_id in recipients:
            try:
                status = await send_with_rate_limit(bot, chat_id)
            except TelegramAPIError as exc:
                failed += 1
                print(f"Failed chat_id={chat_id}: {exc}")
            else:
                await database.record_broadcast_delivery(CAMPAIGN, chat_id, status)
                if status == "sent":
                    sent += 1
                else:
                    blocked += 1
            await asyncio.sleep(0.06)

        print(f"Completed: sent={sent}, blocked={blocked}, failed={failed}")
        return 1 if failed else 0
    finally:
        if bot is not None:
            await bot.session.close()
        await database.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Send the bot update to all existing users")
    parser.add_argument("--dry-run", action="store_true", help="Show count and text only")
    parser.add_argument("--limit", type=int, help="Process no more than this many users")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    raise SystemExit(asyncio.run(broadcast(limit=args.limit, dry_run=args.dry_run)))


if __name__ == "__main__":
    main()
