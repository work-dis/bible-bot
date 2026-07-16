from datetime import UTC, date, datetime

import pytest

from bible_bot.database import Database


@pytest.fixture
async def database(tmp_path):
    db = Database(tmp_path / "bot.db")
    await db.connect()
    yield db
    await db.close()


async def test_user_schedule_and_delivery_claim(database: Database) -> None:
    user = await database.ensure_user(42, "Николай", "Europe/Minsk", "09:00")
    assert user.status == "onboarding"

    next_at = datetime(2026, 7, 17, 6, 0, tzinfo=UTC)
    await database.set_status(42, "active", next_send_at=next_at)
    due = await database.get_due_users(datetime(2026, 7, 17, 6, 1, tzinfo=UTC))
    assert [item.chat_id for item in due] == [42]

    local_date = date(2026, 7, 17)
    assert await database.claim_delivery(42, local_date, "JHN.3.16.17") is True
    assert await database.claim_delivery(42, local_date, "JHN.3.16.17") is False

    following = datetime(2026, 7, 18, 6, 0, tzinfo=UTC)
    await database.complete_delivery(
        42,
        local_date,
        next_send_at=following,
        next_position=1,
        pause=False,
    )
    updated = await database.get_user(42)
    assert updated.status == "active"
    assert updated.mode_position == 1
    assert updated.next_send_at == following


async def test_favorites_toggle(database: Database) -> None:
    await database.ensure_user(7, "Анна", "Europe/Minsk", "09:00")
    assert await database.toggle_favorite(7, "ROM.8.28.28") is True
    assert await database.is_favorite(7, "ROM.8.28.28") is True
    assert await database.favorite_count(7) == 1
    assert await database.toggle_favorite(7, "ROM.8.28.28") is False
    assert await database.favorite_count(7) == 0


async def test_plan_anchor_is_stable(database: Database) -> None:
    first = await database.get_or_create_plan_anchor(date(2026, 7, 16))
    second = await database.get_or_create_plan_anchor(date(2030, 1, 1))
    assert first == second == date(2026, 7, 16)
