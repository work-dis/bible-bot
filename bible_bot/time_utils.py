from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

TIMEZONE_ALIASES = {
    "минск": "Europe/Minsk",
    "москва": "Europe/Moscow",
    "киев": "Europe/Kyiv",
    "варшава": "Europe/Warsaw",
    "алматы": "Asia/Almaty",
}


def parse_clock_time(value: str) -> time:
    try:
        parsed = datetime.strptime(value.strip(), "%H:%M").time()
    except ValueError as exc:
        raise ValueError("Укажите время в формате ЧЧ:ММ, например 09:00") from exc
    return parsed.replace(second=0, microsecond=0)


def format_clock_time(value: time | str) -> str:
    if isinstance(value, str):
        value = parse_clock_time(value)
    return value.strftime("%H:%M")


def normalize_timezone(value: str) -> str:
    candidate = value.strip()
    alias = TIMEZONE_ALIASES.get(candidate.casefold())
    if alias:
        return alias
    validate_timezone(candidate)
    return candidate


def validate_timezone(value: str) -> None:
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(
            "Не удалось найти часовой пояс. Укажите город или значение вроде Europe/Minsk."
        ) from exc


def next_delivery_at(
    timezone_name: str,
    send_time: time | str,
    *,
    now_utc: datetime | None = None,
    force_tomorrow: bool = False,
) -> datetime:
    """Return the next local delivery time converted to UTC.

    ``force_tomorrow`` is used after onboarding and successful delivery so the
    user never receives two scheduled verses on the same local date.
    """

    zone = ZoneInfo(timezone_name)
    clock = parse_clock_time(send_time) if isinstance(send_time, str) else send_time
    current_utc = now_utc or datetime.now(UTC)
    if current_utc.tzinfo is None:
        current_utc = current_utc.replace(tzinfo=UTC)
    local_now = current_utc.astimezone(zone)

    target_date = local_now.date()
    target_local = datetime.combine(target_date, clock, tzinfo=zone)
    if force_tomorrow or target_local <= local_now:
        target_date += timedelta(days=1)
        target_local = datetime.combine(target_date, clock, tzinfo=zone)
    return target_local.astimezone(UTC)
