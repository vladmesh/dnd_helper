from telegram import Update
from telegram.ext import ContextTypes

from dnd_helper_bot.keyboards.main import build_main_menu
from dnd_helper_bot.keyboards.monsters import build_monsters_root_keyboard
from dnd_helper_bot.keyboards.spells import build_spells_root_keyboard


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Выберите действие:", reply_markup=build_main_menu())


async def show_bestiarie_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Бестиарий:", reply_markup=build_monsters_root_keyboard())


async def show_spells_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Заклинания:", reply_markup=build_spells_root_keyboard())


