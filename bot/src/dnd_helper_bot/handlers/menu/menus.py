import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from dnd_helper_bot.keyboards.monsters import build_monsters_root_keyboard
from dnd_helper_bot.keyboards.spells import build_spells_root_keyboard
from dnd_helper_bot.utils.i18n import t

from .i18n import _build_main_menu_inline_i18n
from .settings import _resolve_lang_by_user

logger = logging.getLogger(__name__)


async def show_bestiarie_menu(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = update.effective_chat.id if update.effective_chat else None
    logger.info("Show bestiary menu", extra={"correlation_id": chat_id, "user_id": user_id})
    lang = await _resolve_lang_by_user(update)
    await update.message.reply_text(
        await t("menu.bestiary.title", lang) + ":",
        reply_markup=await build_monsters_root_keyboard(lang),
    )


async def show_spells_menu(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = update.effective_chat.id if update.effective_chat else None
    logger.info("Show spells menu", extra={"correlation_id": chat_id, "user_id": user_id})
    lang = await _resolve_lang_by_user(update)
    await update.message.reply_text(
        await t("menu.spells.title", lang) + ":",
        reply_markup=await build_spells_root_keyboard(lang),
    )


async def show_main_menu_from_callback(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id if query and query.from_user else None
    chat_id = query.message.chat_id if query and query.message else None
    logger.info("Callback to main menu", extra={"correlation_id": chat_id, "user_id": user_id, "callback": getattr(query, 'data', None)})
    await query.answer()
    class _QWrap:
        effective_user = None
        def __init__(self, q):
            self.effective_user = q.from_user if q and getattr(q, "from_user", None) else None
    lang = await _resolve_lang_by_user(_QWrap(query))
    await query.message.edit_text((await t("menu.main.title", lang)) + ":", reply_markup=await _build_main_menu_inline_i18n(lang))


async def show_bestiarie_menu_from_callback(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id if query and query.from_user else None
    chat_id = query.message.chat_id if query and query.message else None
    logger.info("Callback to bestiary menu", extra={"correlation_id": chat_id, "user_id": user_id, "callback": getattr(query, 'data', None)})
    await query.answer()
    class _QWrap:
        effective_user = None
        def __init__(self, q):
            self.effective_user = q.from_user if q and getattr(q, "from_user", None) else None
    lang = await _resolve_lang_by_user(_QWrap(query))
    kb = await build_monsters_root_keyboard(lang)
    rows = list(kb.inline_keyboard)
    back = await t("nav.back", lang)
    main = await t("nav.main", lang)
    rows.append([InlineKeyboardButton(back, callback_data="menu:main"), InlineKeyboardButton(main, callback_data="menu:main")])
    await query.message.edit_text((await t("menu.bestiary.title", lang)) + ":", reply_markup=InlineKeyboardMarkup(rows))


async def show_spells_menu_from_callback(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id if query and query.from_user else None
    chat_id = query.message.chat_id if query and query.message else None
    logger.info("Callback to spells menu", extra={"correlation_id": chat_id, "user_id": user_id, "callback": getattr(query, 'data', None)})
    await query.answer()
    class _QWrap:
        effective_user = None
        def __init__(self, q):
            self.effective_user = q.from_user if q and getattr(q, "from_user", None) else None
    lang = await _resolve_lang_by_user(_QWrap(query))
    kb = await build_spells_root_keyboard(lang)
    rows = list(kb.inline_keyboard)
    back = await t("nav.back", lang)
    main = await t("nav.main", lang)
    rows.append([InlineKeyboardButton(back, callback_data="menu:main"), InlineKeyboardButton(main, callback_data="menu:main")])
    await query.message.edit_text((await t("menu.spells.title", lang)) + ":", reply_markup=InlineKeyboardMarkup(rows))


