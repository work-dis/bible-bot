from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from bible_bot.config import Settings
from bible_bot.content import BibleCatalog
from bible_bot.database import Database, User
from bible_bot.keyboards import (
    completion_keyboard,
    confirmation_keyboard,
    daily_verse_keyboard,
    settings_keyboard,
    stop_confirmation_keyboard,
    themes_keyboard,
    time_keyboard,
    timezone_keyboard,
    welcome_keyboard,
)
from bible_bot.messages import (
    HELP_TEXT,
    activated_text,
    completion_text,
    context_text,
    favorites_text,
    schedule_confirmation_text,
    settings_text,
    verse_text,
    welcome_text,
)
from bible_bot.time_utils import (
    format_clock_time,
    next_delivery_at,
    normalize_timezone,
    parse_clock_time,
)


def create_router(
    database: Database,
    catalog: BibleCatalog,
    settings: Settings,
    anchor_date: date,
) -> Router:
    router = Router(name="bible-bot")
    default_time = format_clock_time(settings.default_time)

    async def ensure_message_user(message: Message) -> User:
        if message.from_user is None:
            raise RuntimeError("A private Telegram user is required")
        return await database.ensure_user(
            message.chat.id,
            message.from_user.first_name or "",
            settings.default_timezone,
            default_time,
        )

    async def require_callback_user(query: CallbackQuery) -> User:
        if query.message is None:
            raise RuntimeError("Callback message is unavailable")
        user = await database.get_user(query.message.chat.id)
        if user is None:
            user = await database.ensure_user(
                query.message.chat.id,
                query.from_user.first_name or "",
                settings.default_timezone,
                default_time,
            )
        return user

    async def show_confirmation(query: CallbackQuery) -> None:
        user = await require_callback_user(query)
        await query.message.edit_text(
            schedule_confirmation_text(user), reply_markup=confirmation_keyboard()
        )

    async def apply_active_schedule(user: User) -> datetime:
        return next_delivery_at(
            user.timezone,
            user.send_time,
            now_utc=datetime.now(UTC),
            force_tomorrow=False,
        )

    async def send_passage(message: Message, chat_id: int, reference_key: str) -> None:
        passage = catalog.get_passage(reference_key)
        saved = await database.is_favorite(chat_id, reference_key)
        await message.answer(
            verse_text(passage),
            reply_markup=daily_verse_keyboard(reference_key, saved=saved),
        )

    async def send_global_today(message: Message, chat_id: int, timezone_name: str) -> None:
        local_date = datetime.now(UTC).astimezone(ZoneInfo(timezone_name)).date()
        selection = catalog.select(
            mode="global",
            position=0,
            local_date=local_date,
            anchor_date=anchor_date,
        )
        await send_passage(message, chat_id, selection.passage_key)

    async def show_settings_message(message: Message, user: User) -> None:
        await message.answer(settings_text(user), reply_markup=settings_keyboard(user.status))

    async def show_favorites_message(message: Message, chat_id: int) -> None:
        keys = await database.list_favorites(chat_id)
        passages = [catalog.get_passage(key) for key in keys]
        await message.answer(favorites_text(passages))

    @router.message(CommandStart())
    async def start(message: Message) -> None:
        user = await ensure_message_user(message)
        await database.clear_pending_input(user.chat_id)
        if user.status in {"active", "paused"}:
            await show_settings_message(message, user)
            return
        await message.answer(
            welcome_text(default_time), reply_markup=welcome_keyboard(default_time)
        )

    @router.callback_query(F.data == "start:quick")
    async def start_quick(query: CallbackQuery) -> None:
        await query.answer()
        user = await require_callback_user(query)
        await database.update_schedule(
            user.chat_id, timezone=settings.default_timezone, send_time=default_time
        )
        await show_confirmation(query)

    @router.callback_query(F.data == "start:confirm")
    async def confirm_start(query: CallbackQuery) -> None:
        await query.answer()
        user = await require_callback_user(query)
        next_at = next_delivery_at(
            user.timezone,
            user.send_time,
            now_utc=datetime.now(UTC),
            force_tomorrow=True,
        )
        await database.set_mode(
            user.chat_id,
            "global",
            position=0,
            status="active",
            next_send_at=next_at,
        )
        user = await database.get_user(user.chat_id)
        await database.clear_pending_input(user.chat_id)
        await query.message.edit_text(activated_text(user))
        await send_global_today(query.message, user.chat_id, user.timezone)

    @router.callback_query(F.data.startswith("time:menu:"))
    async def show_time_menu(query: CallbackQuery) -> None:
        await query.answer()
        origin = query.data.rsplit(":", 1)[1]
        await query.message.edit_text(
            "Когда тебе удобнее получать стих?", reply_markup=time_keyboard(origin)
        )

    @router.callback_query(F.data.startswith("time:set:"))
    async def set_time(query: CallbackQuery) -> None:
        await query.answer()
        _, _, origin, value = query.data.split(":", 3)
        clock = format_clock_time(parse_clock_time(value))
        user = await require_callback_user(query)
        next_at = None
        update_next = user.status == "active"
        if update_next:
            next_at = next_delivery_at(user.timezone, clock, now_utc=datetime.now(UTC))
        await database.update_schedule(
            user.chat_id,
            send_time=clock,
            next_send_at=next_at,
            update_next_send=update_next,
        )
        await database.clear_pending_input(user.chat_id)
        if origin == "start":
            await show_confirmation(query)
        else:
            user = await database.get_user(user.chat_id)
            await query.message.edit_text(
                settings_text(user), reply_markup=settings_keyboard(user.status)
            )

    @router.callback_query(F.data.startswith("time:custom:"))
    async def request_custom_time(query: CallbackQuery) -> None:
        await query.answer()
        origin = query.data.rsplit(":", 1)[1]
        user = await require_callback_user(query)
        await database.set_pending_input(user.chat_id, "time", origin)
        await query.message.edit_text(
            "Напиши время в формате <b>ЧЧ:ММ</b>, например <code>08:30</code>."
        )

    @router.callback_query(F.data.startswith("tz:menu:"))
    async def show_timezone_menu(query: CallbackQuery) -> None:
        await query.answer()
        origin = query.data.rsplit(":", 1)[1]
        await query.message.edit_text(
            "Выбери часовой пояс:", reply_markup=timezone_keyboard(origin)
        )

    @router.callback_query(F.data.startswith("tz:set:"))
    async def set_timezone(query: CallbackQuery) -> None:
        await query.answer()
        _, _, origin, timezone_name = query.data.split(":", 3)
        timezone_name = normalize_timezone(timezone_name)
        user = await require_callback_user(query)
        next_at = None
        update_next = user.status == "active"
        if update_next:
            next_at = next_delivery_at(timezone_name, user.send_time, now_utc=datetime.now(UTC))
        await database.update_schedule(
            user.chat_id,
            timezone=timezone_name,
            next_send_at=next_at,
            update_next_send=update_next,
        )
        await database.clear_pending_input(user.chat_id)
        if origin == "start":
            await show_confirmation(query)
        else:
            user = await database.get_user(user.chat_id)
            await query.message.edit_text(
                settings_text(user), reply_markup=settings_keyboard(user.status)
            )

    @router.callback_query(F.data.startswith("tz:custom:"))
    async def request_custom_timezone(query: CallbackQuery) -> None:
        await query.answer()
        origin = query.data.rsplit(":", 1)[1]
        user = await require_callback_user(query)
        await database.set_pending_input(user.chat_id, "timezone", origin)
        await query.message.edit_text(
            "Напиши город или часовой пояс, например <code>Минск</code> "
            "или <code>Europe/Minsk</code>."
        )

    @router.message(Command("settings"))
    async def settings_command(message: Message) -> None:
        user = await ensure_message_user(message)
        await show_settings_message(message, user)

    @router.callback_query(F.data == "settings:show")
    async def settings_callback(query: CallbackQuery) -> None:
        await query.answer()
        user = await require_callback_user(query)
        await query.message.answer(settings_text(user), reply_markup=settings_keyboard(user.status))

    @router.callback_query(F.data == "settings:pause")
    async def pause_callback(query: CallbackQuery) -> None:
        await query.answer("Рассылка поставлена на паузу")
        user = await require_callback_user(query)
        await database.set_status(user.chat_id, "paused")
        user = await database.get_user(user.chat_id)
        await query.message.edit_text(
            settings_text(user), reply_markup=settings_keyboard(user.status)
        )

    @router.message(Command("pause"))
    async def pause_command(message: Message) -> None:
        user = await ensure_message_user(message)
        await database.set_status(user.chat_id, "paused")
        user = await database.get_user(user.chat_id)
        await show_settings_message(message, user)

    @router.callback_query(F.data == "settings:resume")
    async def resume_callback(query: CallbackQuery) -> None:
        await query.answer("Рассылка возобновлена")
        user = await require_callback_user(query)
        next_at = await apply_active_schedule(user)
        await database.set_status(user.chat_id, "active", next_send_at=next_at)
        user = await database.get_user(user.chat_id)
        await query.message.edit_text(
            settings_text(user), reply_markup=settings_keyboard(user.status)
        )

    @router.callback_query(F.data == "settings:stop_confirm")
    async def stop_confirm(query: CallbackQuery) -> None:
        await query.answer()
        await query.message.edit_text(
            "Отключить ежедневную рассылку? Сохранённые стихи останутся.",
            reply_markup=stop_confirmation_keyboard(),
        )

    @router.callback_query(F.data == "settings:stop")
    async def stop_callback(query: CallbackQuery) -> None:
        await query.answer("Рассылка отключена")
        user = await require_callback_user(query)
        await database.set_status(user.chat_id, "stopped")
        await query.message.edit_text("Рассылка отключена. Чтобы начать снова, отправь /start.")

    @router.message(Command("today"))
    async def today_command(message: Message) -> None:
        user = await ensure_message_user(message)
        await send_global_today(message, user.chat_id, user.timezone)

    @router.callback_query(F.data.startswith("context:"))
    async def show_context(query: CallbackQuery) -> None:
        await query.answer()
        reference_key = query.data.partition(":")[2]
        selected = catalog.get_passage(reference_key)
        context = catalog.get_context(reference_key)
        await query.message.answer(context_text(context, selected))

    @router.callback_query(F.data.startswith("favorite:"))
    async def toggle_favorite(query: CallbackQuery) -> None:
        reference_key = query.data.partition(":")[2]
        user = await require_callback_user(query)
        saved = await database.toggle_favorite(user.chat_id, reference_key)
        await query.answer("Сохранено" if saved else "Удалено из сохранённых")
        await query.message.edit_reply_markup(
            reply_markup=daily_verse_keyboard(reference_key, saved=saved)
        )

    @router.message(Command("favorites"))
    async def favorites_command(message: Message) -> None:
        user = await ensure_message_user(message)
        await show_favorites_message(message, user.chat_id)

    @router.callback_query(F.data == "favorites:show")
    async def favorites_callback(query: CallbackQuery) -> None:
        await query.answer()
        user = await require_callback_user(query)
        await show_favorites_message(query.message, user.chat_id)

    async def activate_cycle(query: CallbackQuery, mode: str, label: str) -> None:
        user = await require_callback_user(query)
        next_at = next_delivery_at(
            user.timezone,
            user.send_time,
            now_utc=datetime.now(UTC),
            force_tomorrow=True,
        )
        await database.set_mode(
            user.chat_id,
            mode,
            position=0,
            status="active",
            next_send_at=next_at,
        )
        await query.message.edit_text(
            f"Готово 🌿\n\nВыбран режим: <b>{label}</b>. Следующий стих придёт завтра "
            f"в <b>{user.send_time}</b>."
        )

    @router.callback_query(F.data == "cycle:restart")
    async def restart_cycle(query: CallbackQuery) -> None:
        await query.answer()
        await activate_cycle(query, "personal", "новый круг")

    @router.callback_query(F.data == "cycle:sequential")
    async def sequential_cycle(query: CallbackQuery) -> None:
        await query.answer()
        await activate_cycle(query, "sequential", "стихи по порядку книг")

    @router.callback_query(F.data == "cycle:themes")
    async def choose_theme(query: CallbackQuery) -> None:
        await query.answer()
        await query.message.edit_text(
            "Какую тему выберем для следующего цикла?",
            reply_markup=themes_keyboard(catalog.theme_labels),
        )

    @router.callback_query(F.data.startswith("cycle:theme:"))
    async def activate_theme(query: CallbackQuery) -> None:
        await query.answer()
        slug = query.data.rsplit(":", 1)[1]
        await activate_cycle(query, f"theme:{slug}", catalog.theme_labels[slug])

    @router.callback_query(F.data == "cycle:back")
    async def cycle_back(query: CallbackQuery) -> None:
        await query.answer()
        user = await require_callback_user(query)
        count = await database.favorite_count(user.chat_id)
        local_date = datetime.now(UTC).astimezone(ZoneInfo(user.timezone)).date()
        cycle_size = catalog.select(
            mode=user.mode,
            position=user.mode_position,
            local_date=local_date,
            anchor_date=anchor_date,
        ).size
        await query.message.edit_text(
            completion_text(count, cycle_size), reply_markup=completion_keyboard(count > 0)
        )

    @router.callback_query(F.data == "cycle:pause")
    async def keep_cycle_paused(query: CallbackQuery) -> None:
        await query.answer("Рассылка остаётся на паузе")
        await query.message.edit_text(
            "Рассылка остаётся на паузе 🌿\n\nВозобновить её можно через /settings."
        )

    @router.message(Command("help"))
    async def help_command(message: Message) -> None:
        await message.answer(HELP_TEXT)

    @router.message(F.text)
    async def receive_pending_input(message: Message) -> None:
        user = await ensure_message_user(message)
        pending = await database.get_pending_input(user.chat_id)
        if pending is None:
            await message.answer("Открой настройки командой /settings или начни с /start.")
            return

        try:
            if pending.action == "time":
                clock = format_clock_time(parse_clock_time(message.text or ""))
                next_at = None
                update_next = user.status == "active"
                if update_next:
                    next_at = next_delivery_at(user.timezone, clock, now_utc=datetime.now(UTC))
                await database.update_schedule(
                    user.chat_id,
                    send_time=clock,
                    next_send_at=next_at,
                    update_next_send=update_next,
                )
            elif pending.action == "timezone":
                timezone_name = normalize_timezone(message.text or "")
                next_at = None
                update_next = user.status == "active"
                if update_next:
                    next_at = next_delivery_at(
                        timezone_name, user.send_time, now_utc=datetime.now(UTC)
                    )
                await database.update_schedule(
                    user.chat_id,
                    timezone=timezone_name,
                    next_send_at=next_at,
                    update_next_send=update_next,
                )
            else:
                await database.clear_pending_input(user.chat_id)
                await message.answer("Не удалось продолжить настройку. Попробуй /settings.")
                return
        except ValueError as exc:
            await message.answer(str(exc))
            return

        await database.clear_pending_input(user.chat_id)
        updated_user = await database.get_user(user.chat_id)
        if updated_user is None:
            raise RuntimeError("User disappeared while updating schedule")
        if pending.origin == "start":
            await message.answer(
                schedule_confirmation_text(updated_user),
                reply_markup=confirmation_keyboard(),
            )
        else:
            await show_settings_message(message, updated_user)

    return router
