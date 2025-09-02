import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from dnd_helper_bot.keyboards.main import build_main_menu_inline  # noqa: E402
from dnd_helper_bot.keyboards.monsters import build_monsters_root_keyboard  # noqa: E402
from dnd_helper_bot.keyboards.spells import build_spells_root_keyboard  # noqa: E402
from dnd_helper_bot.repositories.api_client import api_get_one, api_post, api_patch  # noqa: E402

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = update.effective_chat.id if update.effective_chat else None
    logger.info("Start command received", extra={"correlation_id": chat_id, "user_id": user_id})
    # Ensure registration; if user absent, ask for language and stop
    tg_id = update.effective_user.id if update.effective_user else None
    name = (update.effective_user.full_name or update.effective_user.username or "User") if update.effective_user else "User"
    try:
        user = await api_get_one(f"/users/by-telegram/{tg_id}")
    except Exception:
        user = None

    if not user:
        await update.message.reply_text(
            "Choose language / Выберите язык:",
            reply_markup=_build_language_keyboard(include_back=False),
        )
        return

    lang = user.get("lang") or ((update.effective_user.language_code or "ru").lower().startswith("en") and "en" or "ru")
    await update.message.reply_text(
        "Choose an action:" if lang == "en" else "Выберите действие:",
        reply_markup=build_main_menu_inline(lang),
    )


async def show_bestiarie_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = update.effective_chat.id if update.effective_chat else None
    logger.info("Show bestiary menu", extra={"correlation_id": chat_id, "user_id": user_id})
    lang = (update.effective_user.language_code or "ru").lower().startswith("en") and "en" or "ru"
    await update.message.reply_text(
        "Bestiary:" if lang == "en" else "Бестиарий:",
        reply_markup=build_monsters_root_keyboard(lang),
    )


async def show_spells_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = update.effective_chat.id if update.effective_chat else None
    logger.info("Show spells menu", extra={"correlation_id": chat_id, "user_id": user_id})
    lang = (update.effective_user.language_code or "ru").lower().startswith("en") and "en" or "ru"
    await update.message.reply_text(
        "Spells:" if lang == "en" else "Заклинания:",
        reply_markup=build_spells_root_keyboard(lang),
    )


async def show_main_menu_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id if query and query.from_user else None
    chat_id = query.message.chat_id if query and query.message else None
    logger.info("Callback to main menu", extra={"correlation_id": chat_id, "user_id": user_id, "callback": getattr(query, 'data', None)})
    await query.answer()
    lang = (query.from_user.language_code or "ru").lower().startswith("en") and "en" or "ru"
    await query.message.edit_text("Main menu:" if lang == "en" else "Главное меню:", reply_markup=build_main_menu_inline(lang))


async def show_bestiarie_menu_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id if query and query.from_user else None
    chat_id = query.message.chat_id if query and query.message else None
    logger.info("Callback to bestiary menu", extra={"correlation_id": chat_id, "user_id": user_id, "callback": getattr(query, 'data', None)})
    await query.answer()
    lang = (query.from_user.language_code or "ru").lower().startswith("en") and "en" or "ru"
    await query.message.edit_text("Bestiary:" if lang == "en" else "Бестиарий:", reply_markup=build_monsters_root_keyboard(lang))


async def show_spells_menu_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id if query and query.from_user else None
    chat_id = query.message.chat_id if query and query.message else None
    logger.info("Callback to spells menu", extra={"correlation_id": chat_id, "user_id": user_id, "callback": getattr(query, 'data', None)})
    await query.answer()
    lang = (query.from_user.language_code or "ru").lower().startswith("en") and "en" or "ru"
    await query.message.edit_text("Spells:" if lang == "en" else "Заклинания:", reply_markup=build_spells_root_keyboard(lang))


# --- Settings & Language selection ---

def _build_language_keyboard(include_back: bool = True) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("Русский", callback_data="lang:set:ru"),
            InlineKeyboardButton("English", callback_data="lang:set:en"),
        ],
    ]
    if include_back:
        rows.append([InlineKeyboardButton("⬅️", callback_data="menu:main")])
    return InlineKeyboardMarkup(rows)


async def show_settings_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id if query and query.from_user else None
    chat_id = query.message.chat_id if query and query.message else None
    logger.info("Callback to settings", extra={"correlation_id": chat_id, "user_id": user_id, "callback": getattr(query, 'data', None)})
    await query.answer()
    # Keep text neutral without language dependency
    await query.message.edit_text("Settings:", reply_markup=_build_language_keyboard(include_back=True))


async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = getattr(query, "data", "") or ""
    lang = "ru" if data.endswith(":ru") else "en"

    tg_id = query.from_user.id if query and query.from_user else None
    name = (query.from_user.full_name or query.from_user.username or "User") if query and query.from_user else "User"

    # Try to fetch user by telegram id
    user = None
    try:
        user = await api_get_one(f"/users/by-telegram/{tg_id}")
    except Exception:
        user = None

    try:
        if not user:
            # Create user
            created = await api_post(
                "/users",
                {
                    "telegram_id": tg_id,
                    "name": name,
                    "is_admin": False,
                    "lang": lang,
                },
            )
            user = created
        else:
            # Update language
            await api_patch(f"/users/{user['id']}", {"lang": lang})
    except Exception as exc:
        logger.error("Failed to persist language", extra={"error": str(exc)})
        await query.edit_message_text("Ошибка сохранения настроек. Попробуйте ещё раз.")
        return

    # Show main menu in selected language
    await query.edit_message_text(
        "Main menu:" if lang == "en" else "Главное меню:",
        reply_markup=build_main_menu_inline(lang),
    )

