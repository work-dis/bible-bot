from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import time
from pathlib import Path

from bible_bot.time_utils import parse_clock_time, validate_timezone


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    database_path: Path
    data_dir: Path
    default_time: time
    default_timezone: str
    scheduler_poll_seconds: int
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
            database_path=database_path,
            data_dir=package_dir / "data",
            default_time=parse_clock_time(os.getenv("DEFAULT_TIME", "09:00")),
            default_timezone=default_timezone,
            scheduler_poll_seconds=poll_seconds,
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )
