from __future__ import annotations

from html import escape

from bible_bot.content import Passage
from bible_bot.database import User

STATUS_LABELS = {
    "onboarding": "не настроена",
    "active": "активна",
    "paused": "на паузе",
    "stopped": "отключена",
}

MODE_LABELS = {
    "global": "общая глава дня",
    "personal": "личный круг чтения",
    "sequential": "главы по порядку книг",
}

TELEGRAM_TEXT_LIMIT = 4096
CHAPTER_MESSAGE_LIMIT = 3900
VERSES_PER_SECTION = 5


def welcome_text(default_time: str) -> str:
    return (
        "Привет! 🌿\n\n"
        "Каждый день я буду присылать одну главу Нового Завета "
        "в Синодальном переводе. Текст разделён на небольшие блоки, "
        "чтобы его было удобно читать без спешки.\n\n"
        f"Можно начать с <b>{escape(default_time)}</b> по минскому времени "
        "или выбрать другое время."
    )


def schedule_confirmation_text(user: User) -> str:
    return (
        f"Буду присылать главу каждый день в <b>{escape(user.send_time)}</b>.\n"
        f"Часовой пояс: <code>{escape(user.timezone)}</code>.\n\n"
        "Всё верно?"
    )


def activated_text(user: User) -> str:
    return (
        "Готово! 🌿\n\n"
        f"Первая глава — прямо сейчас. Следующая придёт завтра в "
        f"<b>{escape(user.send_time)}</b>."
    )


def chapter_messages(
    passage: Passage,
    *,
    position: int | None = None,
    cycle_size: int | None = None,
    max_length: int = CHAPTER_MESSAGE_LIMIT,
) -> tuple[str, ...]:
    """Format one chapter as readable Telegram-sized message parts."""

    if not passage.is_full_chapter:
        raise ValueError("chapter_messages expects a complete chapter")
    if max_length > TELEGRAM_TEXT_LIMIT:
        raise ValueError(f"Telegram messages cannot exceed {TELEGRAM_TEXT_LIMIT} characters")
    if (position is None) != (cycle_size is None):
        raise ValueError("position and cycle_size must be provided together")

    body_limit = max_length - 500
    if body_limit < 500:
        raise ValueError("max_length is too small for chapter formatting")

    sections: list[str] = []
    for offset in range(0, len(passage.verses), VERSES_PER_SECTION):
        verses = passage.verses[offset : offset + VERSES_PER_SECTION]
        section = _chapter_section(verses)
        if len(section) <= body_limit:
            sections.append(section)
            continue
        for verse in verses:
            single_verse = _chapter_section((verse,))
            if len(single_verse) > body_limit:
                raise ValueError(f"Verse {passage.reference}:{verse[0]} is too long to format")
            sections.append(single_verse)

    bodies: list[str] = []
    current: list[str] = []
    current_length = 0
    for section in sections:
        separator_length = 2 if current else 0
        if current and current_length + separator_length + len(section) > body_limit:
            bodies.append("\n\n".join(current))
            current = []
            current_length = 0
            separator_length = 0
        current.append(section)
        current_length += separator_length + len(section)
    if current:
        bodies.append("\n\n".join(current))

    total_parts = len(bodies)
    result = []
    for part_number, body in enumerate(bodies, start=1):
        details = [_plural(len(passage.verses), "стих", "стиха", "стихов")]
        if position is not None and cycle_size is not None:
            details.insert(0, f"День {position + 1} из {cycle_size}")
        if total_parts > 1:
            details.append(f"часть {part_number} из {total_parts}")

        header = (
            "📖 <b>Глава дня</b>\n"
            f"<b>{escape(passage.book_name)} · глава {passage.chapter}</b>\n"
            f"<i>{' · '.join(details)}</i>"
        )
        footer = ""
        if part_number == total_parts:
            footer = (
                "\n\n<i>Синодальный перевод</i>\n\n"
                "💭 <b>Для размышления</b>\n"
                "Какой стих из этой главы хочется взять с собой сегодня?"
            )
        message = f"{header}\n\n{body}{footer}"
        if len(message) > max_length:
            raise ValueError(f"Formatted chapter part exceeds {max_length} characters")
        result.append(message)
    return tuple(result)


def _chapter_section(verses: tuple[tuple[int, str], ...]) -> str:
    start = verses[0][0]
    end = verses[-1][0]
    range_label = str(start) if start == end else f"{start}–{end}"
    lines = "\n".join(f"<b>{number}</b>  {escape(text)}" for number, text in verses)
    return f"<b>Стихи {range_label}</b>\n<blockquote>{lines}</blockquote>"


def _plural(value: int, one: str, few: str, many: str) -> str:
    if value % 10 == 1 and value % 100 != 11:
        word = one
    elif value % 10 in {2, 3, 4} and value % 100 not in {12, 13, 14}:
        word = few
    else:
        word = many
    return f"{value} {word}"


def context_text(passage: Passage, selected: Passage) -> str:
    lines = []
    for number, text in passage.verses:
        marker = "➜" if selected.verse_start <= number <= selected.verse_end else "·"
        lines.append(f"{marker} <b>{number}</b> {escape(text)}")
    return f"<b>{escape(passage.book_name)} {passage.chapter}</b>\n\n" + "\n".join(lines)


def settings_text(user: User) -> str:
    mode = MODE_LABELS.get(user.mode)
    if user.mode.startswith("theme:"):
        mode = "тематический цикл"
    return (
        "<b>Настройки рассылки</b>\n\n"
        f"Статус: <b>{STATUS_LABELS[user.status]}</b>\n"
        f"Время: <b>{escape(user.send_time)}</b>\n"
        f"Часовой пояс: <code>{escape(user.timezone)}</code>\n"
        f"Режим: {escape(mode or user.mode)}"
    )


def completion_text(favorite_count: int, cycle_size: int = 260) -> str:
    favorite_line = ""
    if favorite_count:
        favorite_line = (
            "\n\nЗа это время добавлено в сохранённое: "
            f"<b>{favorite_count}</b>."
        )
    return (
        "🌿 <b>Первый круг завершён</b>\n\n"
        f"Мы прочитали {_plural(cycle_size, 'главу', 'главы', 'глав')} Нового Завета. Но Слово "
        "не заканчивается — к нему можно возвращаться снова и каждый раз "
        "замечать что-то новое."
        f"{favorite_line}\n\n"
        "Рассылка поставлена на паузу. Как продолжим?"
    )


def favorites_text(passages: list[Passage]) -> str:
    if not passages:
        return (
            "<b>Сохранённое</b>\n\n"
            "Здесь пока пусто. Нажимай «Сохранить главу» после чтения, "
            "если захочется к ней вернуться."
        )

    lines = ["<b>Сохранённое</b>", ""]
    for passage in passages[:20]:
        if passage.is_full_chapter:
            details = _plural(len(passage.verses), "стих", "стиха", "стихов")
            lines.append(f"• <b>{escape(passage.reference)}</b> · {details}")
            continue
        excerpt = passage.text
        if len(passage.text) > 140:
            excerpt = passage.text[:137].rstrip() + "…"
        lines.append(f"• <b>{escape(passage.reference)}</b> — {escape(excerpt)}")
    if len(passages) > 20:
        lines.extend(["", f"Показаны последние 20 из {len(passages)}."])
    return "\n".join(lines)


HELP_TEXT = (
    "<b>Что умеет бот</b>\n\n"
    "/today — получить сегодняшнюю главу\n"
    "/settings — время, часовой пояс и состояние рассылки\n"
    "/favorites — сохранённые главы\n"
    "/pause — поставить рассылку на паузу\n"
    "/help — эта справка\n\n"
    "Одна глава приходит раз в день. Длинные главы делятся на несколько "
    "последовательных частей. Время рассылки можно изменить в любой момент."
)
