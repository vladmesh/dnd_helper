import logging
import urllib.parse
from typing import Any, Dict, List

from dnd_helper_bot.keyboards.main import build_main_menu_inline
from dnd_helper_bot.repositories.api_client import api_get
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def handle_search_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Dice flow takes precedence if active
    if context.user_data.get("awaiting_dice_count") or context.user_data.get("awaiting_dice_faces"):
        from dnd_helper_bot.handlers.dice import \
            handle_dice_text_input  # local import to avoid cycle
        await handle_dice_text_input(update, context)
        return

    awaiting_monster = bool(context.user_data.get("awaiting_monster_query"))
    awaiting_spell = bool(context.user_data.get("awaiting_spell_query"))
    if not (awaiting_monster or awaiting_spell):
        # Not in search mode: show inline main menu directly
        await update.message.reply_text("Выберите действие:", reply_markup=build_main_menu_inline())
        return

    if awaiting_monster:
        context.user_data.pop("awaiting_monster_query", None)
    if awaiting_spell:
        context.user_data.pop("awaiting_spell_query", None)

    query_text = (update.message.text or "").strip()
    if not query_text:
        logger.warning("Empty search query", extra={"correlation_id": update.effective_chat.id if update.effective_chat else None})
        await update.message.reply_text("Пустой запрос. Повторите.", reply_markup=build_main_menu_inline())
        return

    q = urllib.parse.quote(query_text)
    try:
        if awaiting_monster:
            items: List[Dict[str, Any]] = await api_get(f"/monsters/search?q={q}")
        else:
            items = await api_get(f"/spells/search?q={q}")
    except Exception as exc:
        logger.error("API search request failed", extra={"correlation_id": update.effective_chat.id if update.effective_chat else None, "error": str(exc)})
        await update.message.reply_text("Ошибка при запросе к API.")
        return

    if not items:
        logger.info("Search no results", extra={"correlation_id": update.effective_chat.id if update.effective_chat else None, "query": query_text})
        await update.message.reply_text("Ничего не найдено.", reply_markup=build_main_menu_inline())
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

    rows.append([InlineKeyboardButton("К главному меню", callback_data="menu:main")])
    logger.info("Search results shown", extra={"correlation_id": update.effective_chat.id if update.effective_chat else None, "count": len(rows) - 1})

    markup = InlineKeyboardMarkup(rows)
    await update.message.reply_text("Результаты поиска:", reply_markup=markup)


