from __future__ import annotations

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


def welcome_text(default_time: str) -> str:
    return (
        "Привет! 🌿\n\n"
        "Каждый день я буду присылать одну полную главу Нового Завета "
        "в Синодальном переводе. Если глава не помещается в одно сообщение, "
        "она придёт несколькими последовательными частями.\n\n"
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
                "Какая мысль из этой главы особенно отозвалась сегодня?"
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
    "последовательных частей. Время рассылки можно изменить в любой момент."
)
