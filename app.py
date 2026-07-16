from __future__ import annotations

import asyncio
import logging
import os
import secrets
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Update
from fastapi import FastAPI, Header, HTTPException, Request

from bible_bot.config import Settings
from bible_bot.content import BibleCatalog
from bible_bot.database import Database
from bible_bot.handlers import create_router
from bible_bot.scheduler import DailyScheduler


@dataclass(slots=True)
class Runtime:
    settings: Settings
    database: Database
    bot: Bot
    dispatcher: Dispatcher
    scheduler: DailyScheduler
    anchor_date: date


app = FastAPI(title="Bible Bot", docs_url=None, redoc_url=None)
_runtime: Runtime | None = None
_runtime_lock = asyncio.Lock()


def _same_secret(provided: str | None, expected: str | None) -> bool:
    return bool(provided and expected) and secrets.compare_digest(provided, expected)


def _require_webhook_secret(provided: str | None) -> None:
    expected = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip() or None
    if expected is None:
        raise HTTPException(status_code=503, detail="Telegram webhook is not configured")
    if not _same_secret(provided, expected):
        raise HTTPException(status_code=401, detail="Invalid Telegram webhook secret")


def _require_cron_secret(authorization: str | None) -> None:
    expected = os.getenv("CRON_SECRET", "").strip() or None
    if expected is None:
        raise HTTPException(status_code=503, detail="Delivery trigger is not configured")
    if not _same_secret(authorization, f"Bearer {expected}"):
        raise HTTPException(status_code=401, detail="Invalid delivery secret")


async def get_runtime() -> Runtime:
    global _runtime

    if _runtime is not None:
        return _runtime

    async with _runtime_lock:
        if _runtime is not None:
            return _runtime

        settings = Settings.from_env()
        if settings.database_url is None:
            raise RuntimeError("DATABASE_URL is required on Vercel")

        logging.basicConfig(
            level=getattr(logging, settings.log_level, logging.INFO),
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )

        database = Database(settings.database_url)
        await database.connect()
        anchor_today = datetime.now(ZoneInfo(settings.default_timezone)).date()
        anchor_date = await database.get_or_create_plan_anchor(anchor_today)
        catalog = BibleCatalog.from_data_dir(settings.data_dir)
        bot = Bot(
            token=settings.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        dispatcher = Dispatcher()
        dispatcher.include_router(create_router(database, catalog, settings, anchor_date))
        scheduler = DailyScheduler(
            bot=bot,
            database=database,
            catalog=catalog,
            anchor_date=anchor_date,
            poll_seconds=settings.scheduler_poll_seconds,
        )
        _runtime = Runtime(
            settings=settings,
            database=database,
            bot=bot,
            dispatcher=dispatcher,
            scheduler=scheduler,
            anchor_date=anchor_date,
        )
        return _runtime


@app.get("/")
@app.get("/api/health")
async def health() -> dict[str, str | bool]:
    return {
        "service": "bible-bot",
        "status": "ok",
        "database_configured": bool(os.getenv("DATABASE_URL", "").strip()),
        "webhook_configured": bool(os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()),
        "delivery_configured": bool(os.getenv("CRON_SECRET", "").strip()),
    }


@app.post("/api/telegram")
async def telegram_webhook(
    request: Request,
    telegram_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Api-Secret-Token"),
) -> dict[str, bool | str]:
    _require_webhook_secret(telegram_secret)
    runtime = await get_runtime()
    try:
        update = Update.model_validate(await request.json())
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid Telegram update") from exc

    claimed = await runtime.database.claim_telegram_update(update.update_id)
    if not claimed:
        return {"ok": True, "status": "duplicate"}

    try:
        await runtime.dispatcher.feed_update(runtime.bot, update)
    except Exception:
        await runtime.database.release_telegram_update(update.update_id)
        raise
    return {"ok": True, "status": "processed"}


async def dispatch_due(authorization: str | None) -> dict[str, bool | int]:
    _require_cron_secret(authorization)
    runtime = await get_runtime()
    processed = await runtime.scheduler.dispatch_due()
    return {"ok": True, "processed": processed}


@app.get("/api/cron")
async def cron_get(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> dict[str, bool | int]:
    return await dispatch_due(authorization)


@app.post("/api/cron")
async def cron_post(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> dict[str, bool | int]:
    return await dispatch_due(authorization)
