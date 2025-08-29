import logging
import random

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

ALLOWED_FACES = {2, 3, 4, 6, 8, 10, 12, 20, 100}
MAX_DICE_COUNT = 100


def roll_dice(count: int, faces: int) -> list[int]:
    """Roll `count` dice with `faces` sides each and return the list of rolls."""
    return [random.randint(1, faces) for _ in range(count)]


async def show_dice_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id if update.effective_chat else None
    user_id = update.effective_user.id if update.effective_user else None
    logger.info("Show dice menu", extra={"correlation_id": chat_id, "user_id": user_id})
    # Clear any previous dice flow state
    context.user_data.pop("awaiting_dice_count", None)
    context.user_data.pop("awaiting_dice_faces", None)
    context.user_data.pop("dice_count", None)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("d20", callback_data="dice:d20")],
        [InlineKeyboardButton("d6", callback_data="dice:d6")],
        [InlineKeyboardButton("2d6", callback_data="dice:2d6")],
        [InlineKeyboardButton("Произвольный бросок", callback_data="dice:custom")],
    ])
    await update.message.reply_text("Бросить кубики:", reply_markup=keyboard)


async def dice_roll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    kind = query.data.split(":", 1)[1]
    chat_id = query.message.chat_id if query and query.message else None
    user_id = query.from_user.id if query and query.from_user else None
    if kind == "custom":
        # Start two-step flow: ask for count first
        context.user_data["awaiting_dice_count"] = True
        context.user_data.pop("awaiting_dice_faces", None)
        context.user_data.pop("dice_count", None)
        logger.info("Start dice flow (custom)", extra={"correlation_id": chat_id, "user_id": user_id})
        await query.edit_message_text("Сколько кубиков бросить? (1-100)")
        return
    elif kind == "d20":
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


async def handle_dice_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id if update.effective_chat else None
    user_id = update.effective_user.id if update.effective_user else None
    text = (update.message.text or "").strip()

    if context.user_data.get("awaiting_dice_count"):
        try:
            count = int(text)
        except ValueError:
            logger.warning("Dice count invalid (not int)", extra={"correlation_id": chat_id, "user_id": user_id, "input": text})
            await update.message.reply_text("Введите целое число от 1 до 100")
            return
        if not (1 <= count <= MAX_DICE_COUNT):
            logger.warning("Dice count out of range", extra={"correlation_id": chat_id, "user_id": user_id, "count": count})
            await update.message.reply_text("Количество должно быть от 1 до 100")
            return

        context.user_data["awaiting_dice_count"] = False
        context.user_data["awaiting_dice_faces"] = True
        context.user_data["dice_count"] = count
        logger.info("Dice flow: count accepted", extra={"correlation_id": chat_id, "user_id": user_id, "count": count})
        await update.message.reply_text("Номинал кубика? (разрешены: 2,3,4,6,8,10,12,20,100)")
        return

    if context.user_data.get("awaiting_dice_faces"):
        try:
            faces = int(text)
        except ValueError:
            logger.warning("Dice faces invalid (not int)", extra={"correlation_id": chat_id, "user_id": user_id, "input": text})
            await update.message.reply_text("Введите одно из значений: 2,3,4,6,8,10,12,20,100")
            return
        if faces not in ALLOWED_FACES:
            logger.warning("Dice faces not allowed", extra={"correlation_id": chat_id, "user_id": user_id, "faces": faces})
            await update.message.reply_text("Разрешены только: 2,3,4,6,8,10,12,20,100")
            return

        count = int(context.user_data.get("dice_count", 1))
        rolls = roll_dice(count, faces)
        total = sum(rolls)
        truncated = False
        rolls_display = rolls
        if count > 50:
            rolls_display = rolls[:50]
            truncated = True

        rolls_str = ", ".join(map(str, rolls_display))
        if truncated:
            rolls_str = f"{rolls_str}, ..."

        response_text = f"🎲 {count} × d{faces} → [{rolls_str}], сумма = {total}"
        logger.info(
            "Dice rolled",
            extra={
                "correlation_id": chat_id,
                "user_id": user_id,
                "count": count,
                "faces": faces,
                "sum": total,
                "truncated": truncated,
            },
        )

        # Clear state
        context.user_data.pop("awaiting_dice_faces", None)
        context.user_data.pop("dice_count", None)
        await update.message.reply_text(response_text)
        return

