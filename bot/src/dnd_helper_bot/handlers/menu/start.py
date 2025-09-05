import logging

from telegram.ext import ContextTypes

from dnd_helper_bot.repositories.api_client import api_get_one

from .i18n import _build_main_menu_inline_i18n


logger = logging.getLogger(__name__)


async def start(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = update.effective_chat.id if update.effective_chat else None
    logger.info("Start command received", extra={"correlation_id": chat_id, "user_id": user_id})
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
        reply_markup=await _build_main_menu_inline_i18n(lang),
    )


def _build_language_keyboard(include_back: bool = True):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    rows = [
        [
            InlineKeyboardButton("Русский", callback_data="lang:set:ru"),
            InlineKeyboardButton("English", callback_data="lang:set:en"),
        ],
    ]
    if include_back:
        rows.append([InlineKeyboardButton("⬅️", callback_data="menu:main")])
    return InlineKeyboardMarkup(rows)


