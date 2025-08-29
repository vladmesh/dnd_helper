import logging

from dnd_helper_bot.handlers.dice import show_dice_menu
from dnd_helper_bot.handlers.menu import show_bestiarie_menu, show_spells_menu
from dnd_helper_bot.keyboards.main import build_main_menu
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def handle_menu_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()
    chat_id = update.effective_chat.id if update.effective_chat else None
    user_id = update.effective_user.id if update.effective_user else None
    logger.info("Menu text received", extra={"correlation_id": chat_id, "user_id": user_id, "text": text})
    if text == "Бросить кубики":
        await show_dice_menu(update, context)
    elif text == "Бестиарий":
        await show_bestiarie_menu(update, context)
    elif text == "Заклинания":
        await show_spells_menu(update, context)
    else:
        logger.warning("Unknown menu command", extra={"correlation_id": chat_id, "user_id": user_id, "text": text})
        await update.message.reply_text(
            "Не понимаю команду. Выберите действие:", reply_markup=build_main_menu()
        )


