import logging

from telegram.ext import ContextTypes

from dnd_helper_bot.repositories.api_client import api_get_one
from dnd_helper_bot.utils.i18n import t

from .i18n import _build_main_menu_inline_i18n
from .settings import _build_language_keyboard

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
        # Determine UI language from Telegram for prompt only
        try:
            code = (update.effective_user.language_code or "ru").lower()
            lang_guess = "en" if str(code).startswith("en") else "ru"
        except Exception:
            lang_guess = "ru"
        await update.message.reply_text(
            await t("settings.choose_language_prompt", lang_guess),
            reply_markup=await _build_language_keyboard(include_back=False, lang=lang_guess),
        )
        return

    lang = user.get("lang") or ((update.effective_user.language_code or "ru").lower().startswith("en") and "en" or "ru")
    await update.message.reply_text(
        await t("search.select_action", lang),
        reply_markup=await _build_main_menu_inline_i18n(lang),
    )


