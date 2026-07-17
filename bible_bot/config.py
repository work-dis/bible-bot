from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import time
from pathlib import Path

from bible_bot.time_utils import parse_clock_time, validate_timezone


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    database_url: str | None
    database_path: Path
    data_dir: Path
    default_time: time
    default_timezone: str
    scheduler_poll_seconds: int
    telegram_webhook_secret: str | None
    cron_secret: str | None
    public_channel_id: int | str | None
    log_level: str

    @classmethod
    def from_env(cls) -> Settings:
        token = os.getenv("BOT_TOKEN", "").strip()
        if not token:
            raise RuntimeError("BOT_TOKEN is required")

        package_dir = Path(__file__).resolve().parent
        database_path = Path(os.getenv("DATABASE_PATH", "runtime/bible_bot.db"))
        default_timezone = os.getenv("DEFAULT_TIMEZONE", "Europe/Minsk").strip()
        validate_timezone(default_timezone)

        poll_seconds = int(os.getenv("SCHEDULER_POLL_SECONDS", "30"))
        if poll_seconds < 5:
            raise ValueError("SCHEDULER_POLL_SECONDS must be at least 5")

        return cls(
            bot_token=token,
            database_url=os.getenv("DATABASE_URL", "").strip() or None,
            database_path=database_path,
            data_dir=package_dir / "data",
            default_time=parse_clock_time(os.getenv("DEFAULT_TIME", "09:00")),
            default_timezone=default_timezone,
            scheduler_poll_seconds=poll_seconds,
            telegram_webhook_secret=os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip() or None,
            cron_secret=os.getenv("CRON_SECRET", "").strip() or None,
            public_channel_id=_parse_chat_id(os.getenv("PUBLIC_CHANNEL_ID", "")),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )

    @property
    def database_location(self) -> str | Path:
        return self.database_url or self.database_path


def _parse_chat_id(value: str) -> int | str | None:
    value = value.strip()
    if not value:
        return None
    if value.lstrip("-").isdigit():
        return int(value)
    if value.startswith("@") and len(value) > 1:
        return value
    raise ValueError("PUBLIC_CHANNEL_ID must be a numeric chat id or start with @")
