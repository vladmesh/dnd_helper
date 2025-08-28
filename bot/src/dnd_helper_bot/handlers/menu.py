import logging
from telegram import Update
from telegram.ext import ContextTypes
logger = logging.getLogger(__name__)


from dnd_helper_bot.keyboards.main import build_main_menu
from dnd_helper_bot.keyboards.monsters import build_monsters_root_keyboard
from dnd_helper_bot.keyboards.spells import build_spells_root_keyboard


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = update.effective_chat.id if update.effective_chat else None
    logger.info("Start command received", extra={"correlation_id": chat_id, "user_id": user_id})
    await update.message.reply_text("Выберите действие:", reply_markup=build_main_menu())


async def show_bestiarie_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = update.effective_chat.id if update.effective_chat else None
    logger.info("Show bestiary menu", extra={"correlation_id": chat_id, "user_id": user_id})
    await update.message.reply_text("Бестиарий:", reply_markup=build_monsters_root_keyboard())


async def show_spells_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = update.effective_chat.id if update.effective_chat else None
    logger.info("Show spells menu", extra={"correlation_id": chat_id, "user_id": user_id})
    await update.message.reply_text("Заклинания:", reply_markup=build_spells_root_keyboard())


async def show_main_menu_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id if query and query.from_user else None
    chat_id = query.message.chat_id if query and query.message else None
    logger.info("Callback to main menu", extra={"correlation_id": chat_id, "user_id": user_id, "callback": getattr(query, 'data', None)})
    await query.answer()
    await query.message.reply_text("Главное меню:", reply_markup=build_main_menu())


