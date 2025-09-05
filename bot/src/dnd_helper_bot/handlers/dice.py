import logging
import random

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from dnd_helper_bot.repositories.api_client import api_get_one
from dnd_helper_bot.utils.i18n import t
from dnd_helper_bot.utils.nav import build_nav_row

logger = logging.getLogger(__name__)

ALLOWED_FACES = {2, 3, 4, 6, 8, 10, 12, 20, 100}
MAX_DICE_COUNT = 100


def roll_dice(count: int, faces: int) -> list[int]:
    """Roll `count` dice with `faces` sides each and return the list of rolls."""
    return [random.randint(1, faces) for _ in range(count)]


async def _resolve_lang_by_user(update_or_query) -> str:
    """Prefer DB user's language; fallback to Telegram UI language."""
    try:
        tg_user = None
        if hasattr(update_or_query, "effective_user") and update_or_query.effective_user is not None:
            tg_user = update_or_query.effective_user
        elif hasattr(update_or_query, "from_user") and update_or_query.from_user is not None:
            tg_user = update_or_query.from_user
        tg_id = getattr(tg_user, "id", None)
        if tg_id is not None:
            user = await api_get_one(f"/users/by-telegram/{tg_id}")
            lang = user.get("lang")
            if lang in ("ru", "en"):
                return lang
    except Exception:
        pass
    try:
        code = None
        if hasattr(update_or_query, "effective_user") and update_or_query.effective_user is not None:
            code = (update_or_query.effective_user.language_code or "ru").lower()
        elif hasattr(update_or_query, "from_user") and update_or_query.from_user is not None:
            code = (update_or_query.from_user.language_code or "ru").lower()
        return "en" if str(code).startswith("en") else "ru"
    except Exception:
        return "ru"


async def _nav_row(lang: str) -> list[InlineKeyboardButton]:
    return await build_nav_row(lang, back_callback="menu:main")


async def show_dice_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id if update.effective_chat else None
    user_id = update.effective_user.id if update.effective_user else None
    logger.info("Show dice menu", extra={"correlation_id": chat_id, "user_id": user_id})
    # Clear any previous dice flow state
    context.user_data.pop("awaiting_dice_count", None)
    context.user_data.pop("awaiting_dice_faces", None)
    context.user_data.pop("dice_count", None)
    lang = await _resolve_lang_by_user(update)
    keyboard_rows = [
        [InlineKeyboardButton(await t("dice.quick.d20", lang), callback_data="dice:d20")],
        [InlineKeyboardButton(await t("dice.quick.d6", lang), callback_data="dice:d6")],
        [InlineKeyboardButton(await t("dice.quick.2d6", lang), callback_data="dice:2d6")],
        [InlineKeyboardButton(await t("dice.custom.button", lang), callback_data="dice:custom")],
        await _nav_row(lang),
    ]
    keyboard = InlineKeyboardMarkup(keyboard_rows)
    await update.message.reply_text(await t("dice.menu.title", lang), reply_markup=keyboard)


async def dice_roll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    kind = query.data.split(":", 1)[1]
    chat_id = query.message.chat_id if query and query.message else None
    user_id = query.from_user.id if query and query.from_user else None
    lang = await _resolve_lang_by_user(query)
    if kind == "custom":
        # Start two-step flow: ask for count first
        context.user_data["awaiting_dice_count"] = True
        context.user_data.pop("awaiting_dice_faces", None)
        context.user_data.pop("dice_count", None)
        logger.info("Start dice flow (custom)", extra={"correlation_id": chat_id, "user_id": user_id})
        await query.edit_message_text(
            await t("dice.custom.prompt.count", lang),
            reply_markup=InlineKeyboardMarkup([await _nav_row(lang)]),
        )
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
        text = await t("dice.unknown", lang)
        logger.warning("Unknown dice kind", extra={"correlation_id": chat_id, "user_id": user_id, "kind": kind})
        await query.edit_message_text(text)
        return
    logger.info("Dice rolled", extra={"correlation_id": chat_id, "user_id": user_id, "kind": kind, "result": text})
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([await _nav_row(lang)]))


async def handle_dice_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id if update.effective_chat else None
    user_id = update.effective_user.id if update.effective_user else None
    text = (update.message.text or "").strip()
    lang = await _resolve_lang_by_user(update)

    if context.user_data.get("awaiting_dice_count"):
        try:
            count = int(text)
        except ValueError:
            logger.warning("Dice count invalid (not int)", extra={"correlation_id": chat_id, "user_id": user_id, "input": text})
            await update.message.reply_text(await t("dice.custom.prompt.count", lang), reply_markup=InlineKeyboardMarkup([await _nav_row(lang)]))
            return
        if not (1 <= count <= MAX_DICE_COUNT):
            logger.warning("Dice count out of range", extra={"correlation_id": chat_id, "user_id": user_id, "count": count})
            await update.message.reply_text(await t("dice.custom.error.range", lang), reply_markup=InlineKeyboardMarkup([await _nav_row(lang)]))
            return

        context.user_data["awaiting_dice_count"] = False
        context.user_data["awaiting_dice_faces"] = True
        context.user_data["dice_count"] = count
        logger.info("Dice flow: count accepted", extra={"correlation_id": chat_id, "user_id": user_id, "count": count})
        await update.message.reply_text(await t("dice.custom.prompt.faces", lang), reply_markup=InlineKeyboardMarkup([await _nav_row(lang)]))
        return

    if context.user_data.get("awaiting_dice_faces"):
        try:
            faces = int(text)
        except ValueError:
            logger.warning("Dice faces invalid (not int)", extra={"correlation_id": chat_id, "user_id": user_id, "input": text})
            await update.message.reply_text(await t("dice.custom.prompt.faces", lang), reply_markup=InlineKeyboardMarkup([await _nav_row(lang)]))
            return
        if faces not in ALLOWED_FACES:
            logger.warning("Dice faces not allowed", extra={"correlation_id": chat_id, "user_id": user_id, "faces": faces})
            await update.message.reply_text(await t("dice.custom.error.allowed", lang), reply_markup=InlineKeyboardMarkup([await _nav_row(lang)]))
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
        await update.message.reply_text(response_text, reply_markup=InlineKeyboardMarkup([await _nav_row(lang)]))
        return


async def show_dice_menu_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    lang = await _resolve_lang_by_user(query)
    keyboard_rows = [
        [InlineKeyboardButton(await t("dice.quick.d20", lang), callback_data="dice:d20")],
        [InlineKeyboardButton(await t("dice.quick.d6", lang), callback_data="dice:d6")],
        [InlineKeyboardButton(await t("dice.quick.2d6", lang), callback_data="dice:2d6")],
        [InlineKeyboardButton(await t("dice.custom.button", lang), callback_data="dice:custom")],
        await _nav_row(lang),
    ]
    keyboard = InlineKeyboardMarkup(keyboard_rows)
    await query.edit_message_text(await t("dice.menu.title", lang), reply_markup=keyboard)

