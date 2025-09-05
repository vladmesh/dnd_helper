import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from dnd_helper_bot.repositories.api_client import api_get_one, api_patch, api_post
from dnd_helper_bot.utils.i18n import t


logger = logging.getLogger(__name__)


async def _resolve_lang_by_user(update_or_query) -> str:
    try:
        tg_id = update_or_query.effective_user.id if update_or_query and getattr(update_or_query, "effective_user", None) else None
        if tg_id is not None:
            user = await api_get_one(f"/users/by-telegram/{tg_id}")
            lang = user.get("lang")
            if lang in ("ru", "en"):
                return lang
    except Exception:
        pass
    try:
        code = (update_or_query.effective_user.language_code or "ru").lower()
        return "en" if code.startswith("en") else "ru"
    except Exception:
        return "ru"


async def show_settings_from_callback(update, context) -> None:
    query = update.callback_query
    user_id = query.from_user.id if query and query.from_user else None
    chat_id = query.message.chat_id if query and query.message else None
    logger.info("Callback to settings", extra={"correlation_id": chat_id, "user_id": user_id, "callback": getattr(query, 'data', None)})
    await query.answer()
    class _QWrap:
        effective_user = None
        def __init__(self, q):
            self.effective_user = q.from_user if q and getattr(q, "from_user", None) else None
    lang = await _resolve_lang_by_user(_QWrap(query))
    await query.message.edit_text(await t("menu.settings.title", lang, default="Settings:"), reply_markup=_build_language_keyboard(include_back=True))


def _build_language_keyboard(include_back: bool = True) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("Русский", callback_data="lang:set:ru"),
            InlineKeyboardButton("English", callback_data="lang:set:en"),
        ],
    ]
    if include_back:
        rows.append([InlineKeyboardButton("⬅️", callback_data="menu:main")])
    return InlineKeyboardMarkup(rows)


async def set_language(update, context) -> None:
    query = update.callback_query
    await query.answer()
    data = getattr(query, "data", "") or ""
    lang = "ru" if data.endswith(":ru") else "en"

    tg_id = query.from_user.id if query and query.from_user else None
    name = (query.from_user.full_name or query.from_user.username or "User") if query and query.from_user else "User"

    user = None
    try:
        user = await api_get_one(f"/users/by-telegram/{tg_id}")
    except Exception:
        user = None

    try:
        if not user:
            created = await api_post(
                "/users",
                {
                    "telegram_id": tg_id,
                    "name": name,
                    "is_admin": False,
                    "lang": lang,
                },
            )
            user = created
        else:
            await api_patch(f"/users/{user['id']}", {"lang": lang})
    except Exception as exc:
        logger.error("Failed to persist language", extra={"error": str(exc)})
        await query.edit_message_text("Ошибка сохранения настроек. Попробуйте ещё раз.")
        return

    await query.edit_message_text(
        "Main menu:" if lang == "en" else "Главное меню:",
        reply_markup=await _build_main_menu_inline_i18n(lang),
    )

from .i18n import _build_main_menu_inline_i18n  # noqa: E402


