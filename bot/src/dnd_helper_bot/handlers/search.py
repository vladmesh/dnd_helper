import urllib.parse
from typing import Any, Dict, List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from dnd_helper_bot.keyboards.main import build_main_menu
from dnd_helper_bot.repositories.api_client import api_get


async def handle_search_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    awaiting_monster = bool(context.user_data.get("awaiting_monster_query"))
    awaiting_spell = bool(context.user_data.get("awaiting_spell_query"))
    if not (awaiting_monster or awaiting_spell):
        # Delegate to main menu handler when not in search mode
        from dnd_helper_bot.handlers.text_menu import handle_menu_text  # local import to avoid cycle

        await handle_menu_text(update, context)
        return

    if awaiting_monster:
        context.user_data.pop("awaiting_monster_query", None)
    if awaiting_spell:
        context.user_data.pop("awaiting_spell_query", None)

    query_text = (update.message.text or "").strip()
    if not query_text:
        await update.message.reply_text("Пустой запрос. Повторите.", reply_markup=build_main_menu())
        return

    q = urllib.parse.quote(query_text)
    try:
        if awaiting_monster:
            items: List[Dict[str, Any]] = await api_get(f"/monsters/search?q={q}")
        else:
            items = await api_get(f"/spells/search?q={q}")
    except Exception:
        await update.message.reply_text("Ошибка при запросе к API.")
        return

    if not items:
        await update.message.reply_text("Ничего не найдено.", reply_markup=build_main_menu())
        return

    rows: List[List[InlineKeyboardButton]] = []
    if awaiting_monster:
        for m in items[:10]:
            title = m.get("title") or m.get("description", "<no title>")
            rows.append([InlineKeyboardButton(title, callback_data=f"monster:detail:{m['id']}")])
        rows.append([InlineKeyboardButton("К бестиарию", callback_data="monster:list:page:1")])
    else:
        for s in items[:10]:
            title = s.get("title") or s.get("description", "<no title>")
            rows.append([InlineKeyboardButton(title, callback_data=f"spell:detail:{s['id']}")])
        rows.append([InlineKeyboardButton("К заклинаниям", callback_data="spell:list:page:1")])

    markup = InlineKeyboardMarkup(rows)
    await update.message.reply_text("Результаты поиска:", reply_markup=markup)


