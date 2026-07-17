from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from bible_bot.content import BibleCatalog
from bible_bot.database import Database
from bible_bot.scheduler import DailyScheduler

DATA_DIR = Path(__file__).resolve().parents[1] / "bible_bot" / "data"


class FakeBot:
    def __init__(self) -> None:
        self.messages: list[tuple[int, str]] = []

    async def send_message(self, chat_id: int, text: str, **kwargs) -> None:
        self.messages.append((chat_id, text))


@pytest.fixture
async def database(tmp_path):
    db = Database(tmp_path / "bot.db")
    await db.connect()
    yield db
    await db.close()


async def test_scheduler_sends_once_and_advances(database: Database) -> None:
    catalog = BibleCatalog.from_data_dir(DATA_DIR)
    fake_bot = FakeBot()
    user = await database.ensure_user(123, "Иван", "Europe/Minsk", "09:00")
    due_at = datetime(2026, 7, 16, 6, 0, tzinfo=UTC)
    await database.set_status(user.chat_id, "active", next_send_at=due_at)

    scheduler = DailyScheduler(
        bot=fake_bot,
        database=database,
        catalog=catalog,
        anchor_date=date(2026, 7, 16),
        poll_seconds=30,
    )
    assert await scheduler.dispatch_due() == 1
    assert await scheduler.dispatch_due() == 0

    assert len(fake_bot.messages) == 1
    assert "Синодальный перевод" in fake_bot.messages[0][1]
    updated = await database.get_user(123)
    assert updated.next_send_at > due_at


async def test_scheduler_pauses_after_final_chapter(database: Database) -> None:
    catalog = BibleCatalog.from_data_dir(DATA_DIR)
    fake_bot = FakeBot()
    user = await database.ensure_user(321, "Мария", "Europe/Minsk", "09:00")
    final_day = date(2027, 4, 1)
    due_at = datetime(2027, 4, 1, 6, 0, tzinfo=UTC)
    await database.set_status(user.chat_id, "active", next_send_at=due_at)

    scheduler = DailyScheduler(
        bot=fake_bot,
        database=database,
        catalog=catalog,
        anchor_date=date(2026, 7, 16),
        poll_seconds=30,
    )
    local_date, selection = scheduler._select(await database.get_user(321), due_at)
    assert local_date == final_day
    assert selection.is_final is True

    await scheduler._dispatch_user(await database.get_user(321), due_at)
    updated = await database.get_user(321)
    assert updated.status == "paused"
    assert len(fake_bot.messages) == 2
    assert "Первый круг завершён" in fake_bot.messages[1][1]
