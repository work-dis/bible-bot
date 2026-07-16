from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter

from bible_bot.content import BibleCatalog, PlanSelection
from bible_bot.database import Database, User
from bible_bot.keyboards import completion_keyboard, daily_verse_keyboard
from bible_bot.messages import completion_text, verse_text
from bible_bot.time_utils import next_delivery_at

logger = logging.getLogger(__name__)


class DailyScheduler:
    def __init__(
        self,
        *,
        bot: Bot,
        database: Database,
        catalog: BibleCatalog,
        anchor_date: date,
        poll_seconds: int,
    ) -> None:
        self.bot = bot
        self.database = database
        self.catalog = catalog
        self.anchor_date = anchor_date
        self.poll_seconds = poll_seconds
        self._stop_event = asyncio.Event()

    def stop(self) -> None:
        self._stop_event.set()

    async def run(self) -> None:
        logger.info("Daily scheduler started; plan anchor is %s", self.anchor_date)
        while not self._stop_event.is_set():
            try:
                await self.dispatch_due()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Unexpected scheduler iteration failure")

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.poll_seconds)
            except TimeoutError:
                continue
        logger.info("Daily scheduler stopped")

    async def dispatch_due(self) -> int:
        now = datetime.now(UTC)
        owner = uuid.uuid4().hex
        acquired = await self.database.acquire_scheduler_lock(
            owner,
            now,
            now + timedelta(minutes=10),
        )
        if not acquired:
            logger.info("Another scheduler invocation owns the delivery lock")
            return 0
        try:
            users = await self.database.get_due_users(now)
            for user in users:
                await self._dispatch_user(user, now)
            return len(users)
        finally:
            await self.database.release_scheduler_lock(owner)

    def _select(self, user: User, now: datetime) -> tuple[date, PlanSelection]:
        local_date = now.astimezone(ZoneInfo(user.timezone)).date()
        selection = self.catalog.select(
            mode=user.mode,
            position=user.mode_position,
            local_date=local_date,
            anchor_date=self.anchor_date,
        )
        return local_date, selection

    async def _dispatch_user(self, user: User, now: datetime) -> None:
        local_date, selection = self._select(user, now)
        claimed = await self.database.claim_delivery(
            user.chat_id, local_date, selection.passage_key
        )
        next_at = next_delivery_at(
            user.timezone,
            user.send_time,
            now_utc=now,
            force_tomorrow=True,
        )
        next_position = 0 if user.mode == "global" else selection.position + 1
        if selection.is_final:
            next_position = 0

        if not claimed:
            # A process may have stopped after Telegram accepted the message but
            # before the schedule was advanced. Prefer skipping a possible
            # duplicate over sending the same daily verse twice.
            logger.warning(
                "Existing delivery claim for chat_id=%s local_date=%s; advancing schedule",
                user.chat_id,
                local_date,
            )
            await self.database.complete_delivery(
                user.chat_id,
                local_date,
                next_send_at=next_at,
                next_position=next_position,
                pause=selection.is_final,
            )
            return

        passage = self.catalog.get_passage(selection.passage_key)
        saved = await self.database.is_favorite(user.chat_id, selection.passage_key)
        try:
            await self.bot.send_message(
                user.chat_id,
                verse_text(passage),
                reply_markup=daily_verse_keyboard(selection.passage_key, saved=saved),
            )
        except TelegramForbiddenError:
            logger.info("Bot was blocked by chat_id=%s; stopping delivery", user.chat_id)
            await self.database.release_delivery_claim(user.chat_id, local_date)
            await self.database.set_status(user.chat_id, "stopped")
            return
        except TelegramRetryAfter as exc:
            await self.database.release_delivery_claim(user.chat_id, local_date)
            await self.database.defer_user(
                user.chat_id, datetime.now(UTC) + timedelta(seconds=exc.retry_after + 5)
            )
            return
        except Exception:
            logger.exception("Could not deliver daily verse to chat_id=%s", user.chat_id)
            await self.database.release_delivery_claim(user.chat_id, local_date)
            await self.database.defer_user(user.chat_id, datetime.now(UTC) + timedelta(minutes=10))
            return

        if selection.is_final:
            favorite_count = await self.database.favorite_count(user.chat_id)
            try:
                await self.bot.send_message(
                    user.chat_id,
                    completion_text(favorite_count, selection.size),
                    reply_markup=completion_keyboard(favorite_count > 0),
                )
            except Exception:
                # The verse was already accepted by Telegram. Mark it complete
                # to avoid a duplicate; /settings can resume a paused user.
                logger.exception("Could not send cycle completion to chat_id=%s", user.chat_id)

        await self.database.complete_delivery(
            user.chat_id,
            local_date,
            next_send_at=next_at,
            next_position=next_position,
            pause=selection.is_final,
        )
