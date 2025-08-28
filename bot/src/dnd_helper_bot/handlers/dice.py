import random
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes


logger = logging.getLogger(__name__)

async def show_dice_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id if update.effective_chat else None
    user_id = update.effective_user.id if update.effective_user else None
    logger.info("Show dice menu", extra={"correlation_id": chat_id, "user_id": user_id})
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
    chat_id = query.message.chat_id if query and query.message else None
    user_id = query.from_user.id if query and query.from_user else None
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
        logger.warning("Unknown dice kind", extra={"correlation_id": chat_id, "user_id": user_id, "kind": kind})
        await query.edit_message_text(text)
        return
    logger.info("Dice rolled", extra={"correlation_id": chat_id, "user_id": user_id, "kind": kind, "result": text})
    await query.edit_message_text(text)


