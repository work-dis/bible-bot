from pathlib import Path

import pytest

from bible_bot.content import BibleCatalog
from bible_bot.messages import (
    TELEGRAM_TEXT_LIMIT,
    chapter_messages,
    format_verse_numbers,
    parse_verse_selection,
    public_reflection_text,
    selected_verses_text,
    split_telegram_text,
    welcome_text,
)

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
    assert "На какие дела сегодня вдохновляют прочитанные стихи?" in messages[0]


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


def test_welcome_contains_styled_reading_instructions() -> None:
    text = welcome_text("09:00")

    assert "Что делать теперь" in text
    assert "Помолись Богу" in text
    assert "Напиши, надиктуй аудио или запиши видео" in text
    assert "С БОГОМ!" in text


def test_verse_selection_accepts_numbers_and_ranges() -> None:
    catalog = BibleCatalog.from_data_dir(DATA_DIR)
    chapter = catalog.get_chapter("JHN.3")

    selected = parse_verse_selection("3, 5–7 16; 5", chapter)

    assert selected == (3, 5, 6, 7, 16)
    assert format_verse_numbers(selected) == "3, 5–7, 16"
    assert "Ибо так возлюбил Бог мир" in selected_verses_text(chapter, (16,))


def test_verse_selection_rejects_numbers_outside_chapter() -> None:
    catalog = BibleCatalog.from_data_dir(DATA_DIR)
    chapter = catalog.get_chapter("JHN.3")

    with pytest.raises(ValueError, match="нет стиха 99"):
        parse_verse_selection("99", chapter)

    with pytest.raises(ValueError, match="хотя бы один номер"):
        parse_verse_selection(", ;", chapter)


def test_public_reflection_and_long_text_are_telegram_safe() -> None:
    catalog = BibleCatalog.from_data_dir(DATA_DIR)
    chapter = catalog.get_chapter("JHN.3")
    publication = public_reflection_text(chapter, (3, 16), "Анна", "Дела " * 1000)

    parts = split_telegram_text(publication)

    assert "Анна" in parts[0]
    assert "Иоанна 3 · стихи 3, 16" in parts[0]
    assert "Выбранные стихи:" in parts[0]
    assert "Ибо так возлюбил Бог мир" in parts[0]
    assert all(len(part) <= TELEGRAM_TEXT_LIMIT for part in parts)
