from pathlib import Path

import pytest

from bible_bot.content import BibleCatalog
from bible_bot.keyboards import channel_subscription_keyboard, settings_keyboard
from bible_bot.messages import (
    TELEGRAM_TEXT_LIMIT,
    chapter_messages,
    format_verse_numbers,
    parse_verse_selection,
    public_reflection_text,
    selected_verses_text,
    split_telegram_text,
    telegram_user_url,
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
    publication = public_reflection_text(
        chapter,
        (3, 16),
        "Анна & друзья",
        "<Дела> " * 1000,
        author_url=telegram_user_url(12345),
    )

    parts = split_telegram_text(publication)

    assert '<a href="tg://user?id=12345">Анна &amp; друзья</a>' in parts[0]
    assert "&lt;Дела&gt;" in publication
    assert "Иоанна 3 · стихи 3, 16" in parts[0]
    assert "Выбранные стихи:" in parts[0]
    assert "Ибо так возлюбил Бог мир" in parts[0]
    assert all(len(part) <= TELEGRAM_TEXT_LIMIT for part in parts)


def test_public_channel_subscription_keyboard_uses_channel_username() -> None:
    keyboard = channel_subscription_keyboard("@bible_readers")

    assert keyboard is not None
    assert keyboard.inline_keyboard[0][0].text == "📣 Подписаться на канал"
    assert keyboard.inline_keyboard[0][0].url == "https://t.me/bible_readers"
    assert channel_subscription_keyboard(-1001234567890) is None

    settings = settings_keyboard("active", "@bible_readers")
    channel_buttons = [
        button
        for row in settings.inline_keyboard
        for button in row
        if button.text == "📣 Подписаться на канал"
    ]
    assert len(channel_buttons) == 1
    assert channel_buttons[0].url == "https://t.me/bible_readers"


def test_settings_keyboard_contains_feedback_button() -> None:
    settings = settings_keyboard(
        "active",
        "@bible_readers",
        "https://t.me/bible_feedback",
    )

    feedback_button = next(
        button
        for row in settings.inline_keyboard
        for button in row
        if button.text == "💬 Оставить отзыв"
    )
    assert feedback_button.url == "https://t.me/bible_feedback"


def test_telegram_user_url_prefers_public_username() -> None:
    assert telegram_user_url(12345, "reader") == "https://t.me/reader"
    assert telegram_user_url(12345) == "tg://user?id=12345"


def test_long_escaped_text_is_not_split_inside_html_entity() -> None:
    parts = split_telegram_text("&lt;" * 2000, max_length=101)

    assert all(len(part) <= 101 for part in parts)
    assert all(not part.endswith(("&", "&l", "&lt")) for part in parts)
    assert "".join(parts) == "&lt;" * 2000
