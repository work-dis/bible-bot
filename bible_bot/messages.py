from __future__ import annotations

import re
from html import escape

from bible_bot.content import Chapter
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
TELEGRAM_CAPTION_LIMIT = 1024


def welcome_text(default_time: str) -> str:
    return (
        "Привет! 🌿\n\n"
        "Каждый день я буду присылать одну полную главу Нового Завета "
        "в Синодальном переводе. Если глава не помещается в одно сообщение, "
        "она придёт несколькими последовательными частями.\n\n"
        "🌿 <b>Что делать теперь</b>\n\n"
        "1️⃣ Помолись Богу о наставлении тебя на сей день и читай.\n\n"
        "2️⃣ Делай пометки для себя: какие слова в дела можешь попробовать "
        "применить сегодня.\n\n"
        "3️⃣ Напиши, надиктуй аудио или запиши видео в комментариях: какие "
        "слова в дела берёшь для применения сегодня.\n\n"
        "🙏 <b>С БОГОМ!</b>\n\n"
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
    chapter: Chapter,
    *,
    position: int | None = None,
    cycle_size: int | None = None,
    max_length: int = CHAPTER_MESSAGE_LIMIT,
) -> tuple[str, ...]:
    """Format one chapter as readable Telegram-sized message parts."""

    if max_length > TELEGRAM_TEXT_LIMIT:
        raise ValueError(f"Telegram messages cannot exceed {TELEGRAM_TEXT_LIMIT} characters")
    if (position is None) != (cycle_size is None):
        raise ValueError("position and cycle_size must be provided together")

    body_limit = max_length - 500
    if body_limit < 500:
        raise ValueError("max_length is too small for chapter formatting")

    bodies: list[str] = []
    current: list[str] = []
    for source_line in chapter.lines:
        rendered_line = _chapter_line(source_line, chapter.reference)
        candidate = _chapter_body((*current, rendered_line))
        if current and len(candidate) > body_limit:
            bodies.append(_chapter_body(tuple(current)))
            current = [rendered_line]
            continue
        if len(candidate) > body_limit:
            raise ValueError(f"A line in {chapter.reference} is too long to format")
        current.append(rendered_line)
    if current:
        bodies.append(_chapter_body(tuple(current)))
    if not bodies:
        raise ValueError(f"Chapter has no text: {chapter.reference}")

    total_parts = len(bodies)
    result = []
    for part_number, body in enumerate(bodies, start=1):
        details = []
        if position is not None and cycle_size is not None:
            details.append(f"День {position + 1} из {cycle_size}")
        if total_parts > 1:
            details.append(f"часть {part_number} из {total_parts}")

        header = (
            "📖 <b>Глава дня</b>\n"
            f"<b>{escape(chapter.book_name)} · глава {chapter.number}</b>"
        )
        if details:
            header += f"\n<i>{' · '.join(details)}</i>"
        footer = ""
        if part_number == total_parts:
            footer = (
                "\n\n<i>Синодальный перевод</i>\n\n"
                "💭 <b>Для размышления</b>\n"
                "На какие дела сегодня вдохновляют прочитанные стихи?"
            )
        message = f"{header}\n\n{body}{footer}"
        if len(message) > max_length:
            raise ValueError(f"Formatted chapter part exceeds {max_length} characters")
        result.append(message)
    return tuple(result)


def _chapter_line(source_line: str, reference: str) -> str:
    number, separator, text = source_line.partition("\t")
    if not separator or not number.isdigit() or not text:
        raise ValueError(f"Invalid chapter text line in {reference}")
    return f"<b>{number}</b>  {escape(text)}"


def _chapter_body(lines: tuple[str, ...]) -> str:
    joined_lines = "\n".join(lines)
    return f"<blockquote>{joined_lines}</blockquote>"


def parse_verse_selection(value: str, chapter: Chapter) -> tuple[int, ...]:
    """Parse a selection such as ``3, 5-7 12`` and validate it against a chapter."""

    normalized = value.strip().replace("–", "-").replace("—", "-").replace(";", ",")
    if not normalized:
        raise ValueError("Впиши хотя бы один номер стиха, например <code>3, 16</code>.")

    available = {_verse_number(line, chapter.reference) for line in chapter.lines}
    selected: set[int] = set()
    for token in re.split(r"[\s,]+", normalized):
        if not token:
            continue
        if "-" in token:
            bounds = token.split("-")
            if len(bounds) != 2 or not all(part.isdigit() for part in bounds):
                raise ValueError("Не удалось распознать номера. Пример: <code>3, 5–8, 16</code>.")
            start, end = map(int, bounds)
            if start > end:
                raise ValueError("В диапазоне первый номер должен быть меньше последнего.")
            selected.update(range(start, end + 1))
        elif token.isdigit():
            selected.add(int(token))
        else:
            raise ValueError("Не удалось распознать номера. Пример: <code>3, 5–8, 16</code>.")

    if not selected:
        raise ValueError("Впиши хотя бы один номер стиха, например <code>3, 16</code>.")
    missing = sorted(selected - available)
    if missing:
        max_verse = max(available)
        raise ValueError(
            f"В главе {escape(chapter.reference)} нет стиха {missing[0]}. "
            f"Выбери номера от 1 до {max_verse}."
        )
    return tuple(sorted(selected))


def format_verse_numbers(verse_numbers: tuple[int, ...]) -> str:
    if not verse_numbers:
        return ""

    ranges: list[str] = []
    start = previous = verse_numbers[0]
    for number in verse_numbers[1:]:
        if number == previous + 1:
            previous = number
            continue
        ranges.append(str(start) if start == previous else f"{start}–{previous}")
        start = previous = number
    ranges.append(str(start) if start == previous else f"{start}–{previous}")
    return ", ".join(ranges)


def selected_verses_text(
    chapter: Chapter,
    verse_numbers: tuple[int, ...],
    *,
    max_length: int = CHAPTER_MESSAGE_LIMIT,
) -> str:
    reference = escape(chapter.reference)
    number_text = format_verse_numbers(verse_numbers)
    prefix = f"✅ <b>Выбрано: {reference}, стихи {number_text}</b>\n\n<blockquote>"
    suffix = (
        "</blockquote>\n\n"
        "💭 Теперь отправь размышления текстом, аудио или видео.\n\n"
        "<i>После отправки материал будет опубликован в открытом Telegram-канале.</i>"
    )
    selected = set(verse_numbers)
    rendered: list[str] = []
    truncated = False
    for source_line in chapter.lines:
        number = _verse_number(source_line, chapter.reference)
        if number not in selected:
            continue
        line = _chapter_line(source_line, chapter.reference)
        candidate = "\n".join((*rendered, line))
        if len(prefix) + len(candidate) + len(suffix) > max_length:
            truncated = True
            break
        rendered.append(line)

    if not rendered:
        body = "Выбранные стихи не помещаются в сообщение."
    else:
        body = "\n".join(rendered)
        if truncated:
            body += "\n…"
    return f"{prefix}{body}{suffix}"


def reflection_prompt_text(chapter: Chapter) -> str:
    return (
        "💭 <b>На какие дела сегодня вдохновляют прочитанные стихи?</b>\n\n"
        f"Отправь размышления по главе <b>{escape(chapter.reference)}</b> текстом, "
        "аудио или видео.\n\n"
        "<i>После отправки материал будет опубликован в открытом Telegram-канале.</i>"
    )


def public_reflection_text(
    chapter: Chapter,
    verse_numbers: tuple[int, ...],
    author: str,
    body: str | None = None,
) -> str:
    verse_line = ""
    if verse_numbers:
        verse_line = f" · стихи {format_verse_numbers(verse_numbers)}"
    result = (
        "💭 Размышления после чтения\n"
        f"👤 {author}\n"
        f"📖 {chapter.reference}{verse_line}"
    )
    if verse_numbers:
        selected = set(verse_numbers)
        verse_lines = []
        for source_line in chapter.lines:
            number, _, text = source_line.partition("\t")
            if int(number) in selected:
                verse_lines.append(f"{number}  {text}")
        rendered_verses = "\n".join(verse_lines)
        result += f"\n\nВыбранные стихи:\n{rendered_verses}"
    result += "\n\nНа какие дела сегодня вдохновляют прочитанные стихи?"
    if body:
        result += f"\n\n{body.strip()}"
    return result


def split_telegram_text(text: str, max_length: int = TELEGRAM_TEXT_LIMIT) -> tuple[str, ...]:
    if max_length < 1:
        raise ValueError("max_length must be positive")
    remaining = text.strip()
    parts: list[str] = []
    while len(remaining) > max_length:
        split_at = remaining.rfind("\n", 0, max_length + 1)
        if split_at < max_length // 2:
            split_at = remaining.rfind(" ", 0, max_length + 1)
        if split_at < 1:
            split_at = max_length
        parts.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()
    if remaining:
        parts.append(remaining)
    return tuple(parts)


def _verse_number(source_line: str, reference: str) -> int:
    number, separator, text = source_line.partition("\t")
    if not separator or not number.isdigit() or not text:
        raise ValueError(f"Invalid chapter text line in {reference}")
    return int(number)


def _plural(value: int, one: str, few: str, many: str) -> str:
    if value % 10 == 1 and value % 100 != 11:
        word = one
    elif value % 10 in {2, 3, 4} and value % 100 not in {12, 13, 14}:
        word = few
    else:
        word = many
    return f"{value} {word}"


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


def favorites_text(chapters: list[Chapter]) -> str:
    if not chapters:
        return (
            "<b>Сохранённое</b>\n\n"
            "Здесь пока пусто. Нажимай «Сохранить главу» после чтения, "
            "если захочется к ней вернуться."
        )

    lines = ["<b>Сохранённое</b>", ""]
    for chapter in chapters[:20]:
        lines.append(f"• <b>{escape(chapter.reference)}</b>")
    if len(chapters) > 20:
        lines.extend(["", f"Показаны последние 20 из {len(chapters)}."])
    return "\n".join(lines)


HELP_TEXT = (
    "<b>Что умеет бот</b>\n\n"
    "/today — получить сегодняшнюю главу\n"
    "/settings — время, часовой пояс и состояние рассылки\n"
    "/favorites — сохранённые главы\n"
    "/pause — поставить рассылку на паузу\n"
    "/help — эта справка\n\n"
    "Одна глава приходит раз в день. Длинные главы делятся на несколько "
    "последовательных частей. Под главой можно выделить стихи и отправить "
    "размышления текстом, аудио или видео в открытый канал. Время рассылки "
    "можно изменить в любой момент."
)
