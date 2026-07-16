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
    "global": "общий стих дня",
    "personal": "новый личный круг",
    "sequential": "отобранные стихи по порядку книг",
}


def welcome_text(default_time: str) -> str:
    return (
        "Привет! 🌿\n\n"
        "Каждый день я буду присылать тебе один стих из Нового Завета "
        "в Синодальном переводе — без лишних сообщений, просто небольшая "
        "пауза для размышления.\n\n"
        f"Можно начать с <b>{escape(default_time)}</b> по минскому времени "
        "или выбрать другое время."
    )


def schedule_confirmation_text(user: User) -> str:
    return (
        f"Буду присылать стих каждый день в <b>{escape(user.send_time)}</b>.\n"
        f"Часовой пояс: <code>{escape(user.timezone)}</code>.\n\n"
        "Всё верно?"
    )


def activated_text(user: User) -> str:
    return (
        "Готово! 🌿\n\n"
        f"Первый стих — прямо сейчас. Следующий придёт завтра в "
        f"<b>{escape(user.send_time)}</b>."
    )


def verse_text(passage: Passage) -> str:
    return (
        f"<blockquote>{escape(passage.text)}</blockquote>\n\n"
        f"— <b>{escape(passage.reference)}</b>\n"
        "<i>Синодальный перевод</i>"
    )


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


def completion_text(favorite_count: int, cycle_size: int = 365) -> str:
    favorite_line = ""
    if favorite_count:
        favorite_line = f"\n\nЗа это время ты сохранил(а) стихов: <b>{favorite_count}</b>."
    return (
        "🌿 <b>Первый круг завершён</b>\n\n"
        f"Мы прошли {cycle_size} отобранных отрывков из Нового Завета. Но Слово "
        "не заканчивается — к нему можно возвращаться снова и каждый раз "
        "замечать что-то новое."
        f"{favorite_line}\n\n"
        "Рассылка поставлена на паузу. Как продолжим?"
    )


def favorites_text(passages: list[Passage]) -> str:
    if not passages:
        return (
            "<b>Сохранённые стихи</b>\n\n"
            "Здесь пока пусто. Нажимай «🤍 Сохранить» под стихами, "
            "к которым захочется вернуться."
        )

    lines = ["<b>Сохранённые стихи</b>", ""]
    for passage in passages[:20]:
        excerpt = passage.text
        if len(excerpt) > 140:
            excerpt = excerpt[:137].rstrip() + "…"
        lines.append(f"• <b>{escape(passage.reference)}</b> — {escape(excerpt)}")
    if len(passages) > 20:
        lines.extend(["", f"Показаны последние 20 из {len(passages)}."])
    return "\n".join(lines)


HELP_TEXT = (
    "<b>Что умеет бот</b>\n\n"
    "/today — получить сегодняшний стих\n"
    "/settings — время, часовой пояс и состояние рассылки\n"
    "/favorites — сохранённые стихи\n"
    "/pause — поставить рассылку на паузу\n"
    "/help — эта справка\n\n"
    "Основная рассылка приходит один раз в день. Время можно изменить в любой момент."
)
