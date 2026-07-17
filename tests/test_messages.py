from pathlib import Path

import pytest

from bible_bot.content import BibleCatalog
from bible_bot.messages import TELEGRAM_TEXT_LIMIT, chapter_messages

DATA_DIR = Path(__file__).resolve().parents[1] / "bible_bot" / "data"


def test_short_chapter_is_structured_as_one_message() -> None:
    catalog = BibleCatalog.from_data_dir(DATA_DIR)
    chapter = catalog.get_passage("1CO.13.1.13")

    messages = chapter_messages(chapter, position=7, cycle_size=260)

    assert len(messages) == 1
    assert "<b>1 Коринфянам · глава 13</b>" in messages[0]
    assert "День 8 из 260" in messages[0]
    assert "<b>Стихи 1–5</b>" in messages[0]
    assert "<b>Стихи 11–13</b>" in messages[0]
    assert "Для размышления" in messages[0]


def test_long_chapter_is_split_into_numbered_telegram_safe_parts() -> None:
    catalog = BibleCatalog.from_data_dir(DATA_DIR)
    chapter = catalog.get_passage("MAT.26.1.75")

    messages = chapter_messages(chapter, position=25, cycle_size=260)

    assert len(messages) > 1
    assert all(len(message) <= TELEGRAM_TEXT_LIMIT for message in messages)
    for part_number, message in enumerate(messages, start=1):
        assert f"часть {part_number} из {len(messages)}" in message
        assert "<b>Матфея · глава 26</b>" in message
    assert "Для размышления" not in messages[0]
    assert "Для размышления" in messages[-1]


def test_formatter_rejects_a_partial_passage() -> None:
    catalog = BibleCatalog.from_data_dir(DATA_DIR)

    with pytest.raises(ValueError, match="complete chapter"):
        chapter_messages(catalog.get_passage("JHN.3.16.17"))
