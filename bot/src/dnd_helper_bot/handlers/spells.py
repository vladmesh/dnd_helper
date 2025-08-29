import logging
import random
from typing import Any, Dict, List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from dnd_helper_bot.repositories.api_client import api_get, api_get_one
from dnd_helper_bot.utils.pagination import paginate

logger = logging.getLogger(__name__)


async def spells_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    page = int(query.data.split(":")[-1])
    logger.info("Spells list requested", extra={"correlation_id": query.message.chat_id if query and query.message else None, "page": page})
    all_spells: List[Dict[str, Any]] = await api_get("/spells")
    total = len(all_spells)
    if total == 0:
        logger.warning("No spells available", extra={"correlation_id": query.message.chat_id if query and query.message else None})
        await query.edit_message_text("Заклинаний нет.")
        return
    page_items = paginate(all_spells, page)
    rows: List[List[InlineKeyboardButton]] = []
    for s in page_items:
        label = f"Подробнее: {s.get('description','')} (#{s.get('id')})"
        rows.append([InlineKeyboardButton(label, callback_data=f"spell:detail:{s['id']}")])
    nav: List[InlineKeyboardButton] = []
    if (page - 1) * 5 > 0:
        nav.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"spell:list:page:{page-1}"))
    if page * 5 < total:
        nav.append(InlineKeyboardButton("➡️ Далее", callback_data=f"spell:list:page:{page+1}"))
    if nav:
        rows.append(nav)
    markup = InlineKeyboardMarkup(rows)
    await query.edit_message_text(f"Список заклинаний (стр. {page})", reply_markup=markup)


async def spell_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    spell_id = int(query.data.split(":")[-1])
    logger.info("Spell detail requested", extra={"correlation_id": query.message.chat_id if query and query.message else None, "spell_id": spell_id})
    s = await api_get_one(f"/spells/{spell_id}")
    text = (
        f"{s.get('description','')}\n"
        f"Class: {s.get('caster_class','-')}\n"
        f"Distance: {s.get('distance','-')}, School: {s.get('school','-')}"
    )
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("К списку", callback_data="spell:list:page:1")]])
    await query.edit_message_text(text, reply_markup=markup)


async def spell_random(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    logger.info("Spell random requested", extra={"correlation_id": query.message.chat_id if query and query.message else None})
    all_spells = await api_get("/spells")
    if not all_spells:
        logger.warning("No spells available for random", extra={"correlation_id": query.message.chat_id if query and query.message else None})
        await query.edit_message_text("Заклинаний нет.")
        return
    s = random.choice(all_spells)
    text = (
        f"{s.get('description','')}" + " (random)\n"
        f"Class: {s.get('caster_class','-')}\n"
        f"Distance: {s.get('distance','-')}, School: {s.get('school','-')}"
    )
    await query.edit_message_text(text)


async def spell_search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    context.user_data["awaiting_spell_query"] = True
    logger.info("Spell search prompt shown", extra={"correlation_id": query.message.chat_id if query and query.message else None})
    await query.edit_message_text("Введите подстроку для поиска по названию заклинания:")


