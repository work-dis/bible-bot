from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def welcome_keyboard(default_time: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"🌿 Начать в {default_time}", callback_data="start:quick")],
            [InlineKeyboardButton(text="🕒 Выбрать время", callback_data="time:menu:start")],
        ]
    )


def time_keyboard(origin: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🌅 07:00", callback_data=f"time:set:{origin}:07:00"),
                InlineKeyboardButton(text="☀️ 09:00", callback_data=f"time:set:{origin}:09:00"),
            ],
            [
                InlineKeyboardButton(text="🌤 13:00", callback_data=f"time:set:{origin}:13:00"),
                InlineKeyboardButton(text="🌙 21:00", callback_data=f"time:set:{origin}:21:00"),
            ],
            [InlineKeyboardButton(text="⌨️ Другое время", callback_data=f"time:custom:{origin}")],
        ]
    )


def confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, начать", callback_data="start:confirm")],
            [InlineKeyboardButton(text="🌍 Изменить часовой пояс", callback_data="tz:menu:start")],
            [InlineKeyboardButton(text="↩️ Выбрать другое время", callback_data="time:menu:start")],
        ]
    )


def timezone_keyboard(origin: str) -> InlineKeyboardMarkup:
    zones = [
        ("Минск", "Europe/Minsk"),
        ("Москва", "Europe/Moscow"),
        ("Киев", "Europe/Kyiv"),
        ("Варшава", "Europe/Warsaw"),
        ("Алматы", "Asia/Almaty"),
    ]
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"tz:set:{origin}:{timezone_name}")]
        for label, timezone_name in zones
    ]
    rows.append([InlineKeyboardButton(text="⌨️ Другой город", callback_data=f"tz:custom:{origin}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def daily_verse_keyboard(reference_key: str, *, saved: bool = False) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📖 Показать контекст", callback_data=f"context:{reference_key}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❤️ Сохранено" if saved else "🤍 Сохранить",
                    callback_data=f"favorite:{reference_key}",
                ),
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings:show"),
            ],
        ]
    )


def settings_keyboard(status: str) -> InlineKeyboardMarkup:
    state_button = (
        InlineKeyboardButton(text="⏸ Приостановить", callback_data="settings:pause")
        if status == "active"
        else InlineKeyboardButton(text="▶️ Возобновить", callback_data="settings:resume")
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🕒 Изменить время", callback_data="time:menu:settings")],
            [InlineKeyboardButton(text="🌍 Часовой пояс", callback_data="tz:menu:settings")],
            [InlineKeyboardButton(text="🤍 Мои стихи", callback_data="favorites:show")],
            [state_button],
            [
                InlineKeyboardButton(
                    text="🔕 Отключить рассылку", callback_data="settings:stop_confirm"
                )
            ],
        ]
    )


def stop_confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔕 Да, отключить", callback_data="settings:stop")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="settings:show")],
        ]
    )


def completion_keyboard(has_favorites: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="🔄 Начать новый круг", callback_data="cycle:restart")],
        [InlineKeyboardButton(text="📖 Стихи по порядку книг", callback_data="cycle:sequential")],
        [InlineKeyboardButton(text="🎯 Выбрать тему", callback_data="cycle:themes")],
    ]
    if has_favorites:
        rows.append(
            [InlineKeyboardButton(text="🤍 Мои сохранённые стихи", callback_data="favorites:show")]
        )
    rows.append([InlineKeyboardButton(text="🌿 Оставить паузу", callback_data="cycle:pause")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def themes_keyboard(labels: dict[str, str]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"cycle:theme:{slug}")]
        for slug, label in labels.items()
    ]
    rows.append([InlineKeyboardButton(text="↩️ Назад", callback_data="cycle:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
