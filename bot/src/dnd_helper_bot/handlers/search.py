import logging
import urllib.parse
from typing import Any, Dict, List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from dnd_helper_bot.utils.i18n import t  # noqa: E402
from dnd_helper_bot.utils.nav import build_nav_row  # noqa: E402
from dnd_helper_bot.handlers.menu import _build_language_keyboard, _build_main_menu_inline_i18n  # noqa: E402
from dnd_helper_bot.repositories.api_client import api_get, api_get_one

logger = logging.getLogger(__name__)


async def handle_search_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Dice flow takes precedence if active
    if context.user_data.get("awaiting_dice_count") or context.user_data.get("awaiting_dice_faces"):
        from dnd_helper_bot.handlers.dice import (
            handle_dice_text_input,  # local import to avoid cycle
        )
        await handle_dice_text_input(update, context)
        return

    # Ensure user exists; if not, ask for language first
    try:
        tg_id = update.effective_user.id if update.effective_user else None
        user = await api_get_one(f"/users/by-telegram/{tg_id}")
        lang = user.get("lang", "ru")
    except Exception:
        logger.exception("Failed to fetch user by telegram id")
        # Not registered: show only language selection keyboard (no back)
        # Determine UI language from Telegram
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

    awaiting_monster = bool(context.user_data.get("awaiting_monster_query"))
    awaiting_spell = bool(context.user_data.get("awaiting_spell_query"))
    if not (awaiting_monster or awaiting_spell):
        # Not in search mode: show inline main menu directly
        await update.message.reply_text(
            await t("search.select_action", lang),
            reply_markup=await _build_main_menu_inline_i18n(lang),
        )
        return

    if awaiting_monster:
        context.user_data.pop("awaiting_monster_query", None)
    if awaiting_spell:
        context.user_data.pop("awaiting_spell_query", None)

    query_text = (update.message.text or "").strip()
    if not query_text:
        logger.warning("Empty search query", extra={"correlation_id": update.effective_chat.id if update.effective_chat else None})
        await update.message.reply_text(
            await t("search.empty_query", lang),
            reply_markup=await _build_main_menu_inline_i18n(lang),
        )
        return

    try:
        params = {"q": query_text, "lang": lang}
        logger.info(
            "Search request",
            extra={
                "correlation_id": update.effective_chat.id if update.effective_chat else None,
                "q": query_text,
                "lang": lang,
                "target": "monsters" if awaiting_monster else "spells",
            },
        )
        if awaiting_monster:
            items: List[Dict[str, Any]] = await api_get("/monsters/search-wrapped", params=params)
        else:
            items = await api_get("/spells/search-wrapped", params=params)
        logger.info(
            "Search response",
            extra={
                "correlation_id": update.effective_chat.id if update.effective_chat else None,
                "count": len(items) if isinstance(items, list) else None,
                "sample_keys": (list(items[0].keys()) if isinstance(items, list) and items else []),
            },
        )
    except Exception as exc:
        logger.exception("API search request failed")
        await update.message.reply_text(await t("search.api_error", lang))
        return

    if not items:
        logger.info("Search no results", extra={"correlation_id": update.effective_chat.id if update.effective_chat else None, "query": query_text})
        back_cb = "menu:monsters" if awaiting_monster else "menu:spells"
        nav = await build_nav_row(lang, back_cb)
        markup = InlineKeyboardMarkup([nav])
        await update.message.reply_text(await t("search.no_results", lang), reply_markup=markup)
        return

    rows: List[List[InlineKeyboardButton]] = []
    if awaiting_monster:
        for m in items[:10]:
            try:
                e = m.get("entity") or {}
                tr = m.get("translation") or {}
                mid = e.get("id")
                if mid is None:
                    logger.warning("Search item missing entity.id", extra={"item_keys": list(m.keys())})
                    continue
                label = tr.get("name") or tr.get("description") or "<no name>"
                if not tr.get("name"):
                    logger.info("Search item label from description", extra={"id": mid})
                rows.append([InlineKeyboardButton(str(label), callback_data=f"monster:detail:{mid}")])
            except Exception:
                logger.exception("Failed to render monster search item")
    else:
        for s in items[:10]:
            try:
                e = s.get("entity") or {}
                tr = s.get("translation") or {}
                sid = e.get("id")
                if sid is None:
                    logger.warning("Search item missing entity.id", extra={"item_keys": list(s.keys())})
                    continue
                label = tr.get("name") or tr.get("description") or "<no name>"
                if not tr.get("name"):
                    logger.info("Search item label from description", extra={"id": sid})
                rows.append([InlineKeyboardButton(str(label), callback_data=f"spell:detail:{sid}")])
            except Exception:
                logger.exception("Failed to render spell search item")

    rows.append([InlineKeyboardButton(await t("nav.main", lang), callback_data="menu:main")])
    logger.info("Search results shown", extra={"correlation_id": update.effective_chat.id if update.effective_chat else None, "count": len(rows) - 1})

    markup = InlineKeyboardMarkup(rows)
    await update.message.reply_text(await t("search.results_title", lang), reply_markup=markup)


