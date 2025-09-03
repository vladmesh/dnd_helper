import logging
import urllib.parse
from typing import Any, Dict, List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from dnd_helper_bot.keyboards.main import build_main_menu_inline
from dnd_helper_bot.handlers.menu import _build_language_keyboard  # noqa: E402
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
        # Not registered: show only language selection keyboard (no back)
        await update.message.reply_text(
            "Выберите язык для начала / Choose language first:",
            reply_markup=_build_language_keyboard(include_back=False),
        )
        return

    awaiting_monster = bool(context.user_data.get("awaiting_monster_query"))
    awaiting_spell = bool(context.user_data.get("awaiting_spell_query"))
    if not (awaiting_monster or awaiting_spell):
        # Not in search mode: show inline main menu directly
        await update.message.reply_text("Choose an action:" if lang == "en" else "Выберите действие:", reply_markup=build_main_menu_inline(lang))
        return

    if awaiting_monster:
        context.user_data.pop("awaiting_monster_query", None)
    if awaiting_spell:
        context.user_data.pop("awaiting_spell_query", None)

    query_text = (update.message.text or "").strip()
    if not query_text:
        logger.warning("Empty search query", extra={"correlation_id": update.effective_chat.id if update.effective_chat else None})
        await update.message.reply_text("Empty query. Repeat." if lang == "en" else "Пустой запрос. Повторите.", reply_markup=build_main_menu_inline(lang))
        return

    try:
        params = {"q": query_text, "lang": lang}
        if awaiting_monster:
            items: List[Dict[str, Any]] = await api_get("/monsters/search", params=params)
        else:
            items = await api_get("/spells/search", params=params)
    except Exception as exc:
        logger.error("API search request failed", extra={"correlation_id": update.effective_chat.id if update.effective_chat else None, "error": str(exc)})
        await update.message.reply_text("API request error." if lang == "en" else "Ошибка при запросе к API.")
        return

    if not items:
        logger.info("Search no results", extra={"correlation_id": update.effective_chat.id if update.effective_chat else None, "query": query_text})
        await update.message.reply_text("No results." if lang == "en" else "Ничего не найдено.", reply_markup=build_main_menu_inline(lang))
        return

    rows: List[List[InlineKeyboardButton]] = []
    if awaiting_monster:
        for m in items[:10]:
            label = m.get("name") or m.get("description", "<no name>")
            rows.append([InlineKeyboardButton(label, callback_data=f"monster:detail:{m['id']}")])
    else:
        for s in items[:10]:
            label = s.get("name") or s.get("description", "<no name>")
            rows.append([InlineKeyboardButton(label, callback_data=f"spell:detail:{s['id']}")])

    rows.append([InlineKeyboardButton("Main menu" if lang == "en" else "К главному меню", callback_data="menu:main")])
    logger.info("Search results shown", extra={"correlation_id": update.effective_chat.id if update.effective_chat else None, "count": len(rows) - 1})

    markup = InlineKeyboardMarkup(rows)
    await update.message.reply_text("Search results:" if lang == "en" else "Результаты поиска:", reply_markup=markup)


