import random

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes


async def show_dice_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("d20", callback_data="dice:d20")], #TODO change to text or other option
        [InlineKeyboardButton("d6", callback_data="dice:d6")],
        [InlineKeyboardButton("2d6", callback_data="dice:2d6")],
    ])
    await update.message.reply_text("Бросить кубики:", reply_markup=keyboard)


async def dice_roll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    kind = query.data.split(":", 1)[1]
    if kind == "d20":
        result = random.randint(1, 20)
        text = f"🎲 d20 → {result}"
    elif kind == "d6":
        result = random.randint(1, 6)
        text = f"🎲 d6 → {result}"
    elif kind == "2d6":
        r1, r2 = random.randint(1, 6), random.randint(1, 6)
        text = f"🎲 2d6 → {r1}+{r2} = {r1 + r2}"
    else:
        text = "Неизвестный бросок"
    await query.edit_message_text(text)


