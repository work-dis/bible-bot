from datetime import UTC, datetime

import pytest

from bible_bot.time_utils import next_delivery_at, normalize_timezone, parse_clock_time


def test_parse_clock_time() -> None:
    assert parse_clock_time("09:30").isoformat(timespec="minutes") == "09:30"


def test_parse_clock_time_rejects_invalid_value() -> None:
    with pytest.raises(ValueError, match="ЧЧ:ММ"):
        parse_clock_time("25:99")


def test_next_delivery_uses_local_timezone() -> None:
    now = datetime(2026, 7, 16, 5, 0, tzinfo=UTC)  # 08:00 in Minsk
    assert next_delivery_at("Europe/Minsk", "09:00", now_utc=now) == datetime(
        2026, 7, 16, 6, 0, tzinfo=UTC
    )


def test_force_tomorrow_prevents_second_daily_message() -> None:
    now = datetime(2026, 7, 16, 5, 0, tzinfo=UTC)
    assert next_delivery_at("Europe/Minsk", "09:00", now_utc=now, force_tomorrow=True) == datetime(
        2026, 7, 17, 6, 0, tzinfo=UTC
    )


def test_timezone_alias() -> None:
    assert normalize_timezone("Минск") == "Europe/Minsk"
