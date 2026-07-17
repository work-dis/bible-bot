from pathlib import Path

from bible_bot.content import BibleCatalog
from bible_bot.messages import TELEGRAM_TEXT_LIMIT, chapter_messages

DATA_DIR = Path(__file__).resolve().parents[1] / "bible_bot" / "data"


def test_short_chapter_is_structured_as_one_message() -> None:
    catalog = BibleCatalog.from_data_dir(DATA_DIR)
    chapter = catalog.get_chapter("1CO.13")

    messages = chapter_messages(chapter, position=7, cycle_size=260)

    assert len(messages) == 1
    assert "<b>1 Коринфянам · глава 13</b>" in messages[0]
    assert "День 8 из 260" in messages[0]
    assert "Стихи" not in messages[0]
    assert "<b>1</b>" in messages[0]
    assert "<b>13</b>" in messages[0]
    assert "Если я говорю языками человеческими" in messages[0]
    assert "А теперь пребывают сии три" in messages[0]
    assert "Для размышления" in messages[0]


def test_long_chapter_is_split_into_numbered_telegram_safe_parts() -> None:
    catalog = BibleCatalog.from_data_dir(DATA_DIR)
    chapter = catalog.get_chapter("MAT.26")

    messages = chapter_messages(chapter, position=25, cycle_size=260)

    assert len(messages) > 1
    assert all(len(message) <= TELEGRAM_TEXT_LIMIT for message in messages)
    for part_number, message in enumerate(messages, start=1):
        assert f"часть {part_number} из {len(messages)}" in message
        assert "<b>Матфея · глава 26</b>" in message
    assert "<b>1</b>" in messages[0]
    assert "<b>75</b>" in messages[-1]
    assert "Для размышления" not in messages[0]
    assert "Для размышления" in messages[-1]
