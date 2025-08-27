from telegram import Update
from telegram.ext import ContextTypes

from dnd_helper_bot.handlers.dice import show_dice_menu
from dnd_helper_bot.handlers.menu import show_bestiarie_menu, show_spells_menu
from dnd_helper_bot.keyboards.main import build_main_menu


async def handle_menu_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()
    if text == "Бросить кубики":
        await show_dice_menu(update, context)
    elif text == "Бестиарий":
        await show_bestiarie_menu(update, context)
    elif text == "Заклинания":
        await show_spells_menu(update, context)
    else:
        await update.message.reply_text(
            "Не понимаю команду. Выберите действие:", reply_markup=build_main_menu()
        )


