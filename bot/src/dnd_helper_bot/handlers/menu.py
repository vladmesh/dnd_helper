import logging

from telegram import Update
from telegram.ext import ContextTypes

from dnd_helper_bot.keyboards.main import build_main_menu_inline  # noqa: E402
from dnd_helper_bot.keyboards.monsters import build_monsters_root_keyboard  # noqa: E402
from dnd_helper_bot.keyboards.spells import build_spells_root_keyboard  # noqa: E402

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = update.effective_chat.id if update.effective_chat else None
    logger.info("Start command received", extra={"correlation_id": chat_id, "user_id": user_id})
    lang = (update.effective_user.language_code or "ru").lower().startswith("en") and "en" or "ru"
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


