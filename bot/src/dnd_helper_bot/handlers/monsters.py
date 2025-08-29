import logging
import random
from typing import Any, Dict, List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from dnd_helper_bot.repositories.api_client import api_get, api_get_one
from dnd_helper_bot.utils.pagination import paginate

logger = logging.getLogger(__name__)


async def monsters_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    page = int(query.data.split(":")[-1])
    logger.info("Monsters list requested", extra={"correlation_id": query.message.chat_id if query and query.message else None, "page": page})
    all_monsters: List[Dict[str, Any]] = await api_get("/monsters")
    total = len(all_monsters)
    if total == 0:
        logger.warning("No monsters available", extra={"correlation_id": query.message.chat_id if query and query.message else None})
        await query.edit_message_text("Монстров нет.")
        return
    page_items = paginate(all_monsters, page)
    rows: List[List[InlineKeyboardButton]] = []
    for m in page_items:
        label = f"Подробнее: {m.get('description','')} (#{m.get('id')})"
        rows.append([InlineKeyboardButton(label, callback_data=f"monster:detail:{m['id']}")])
    nav: List[InlineKeyboardButton] = []
    if (page - 1) * 5 > 0:
        nav.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"monster:list:page:{page-1}"))
    if page * 5 < total:
        nav.append(InlineKeyboardButton("➡️ Далее", callback_data=f"monster:list:page:{page+1}"))
    if nav:
        rows.append(nav)
    markup = InlineKeyboardMarkup(rows)
    await query.edit_message_text(f"Список монстров (стр. {page})", reply_markup=markup)


async def monster_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    monster_id = int(query.data.split(":")[-1])
    logger.info("Monster detail requested", extra={"correlation_id": query.message.chat_id if query and query.message else None, "monster_id": monster_id})
    m = await api_get_one(f"/monsters/{monster_id}")
    text = (
        f"{m.get('description','')}\n"
        f"Danger: {m.get('dangerous_lvl','-')}\n"
        f"HP: {m.get('hp','-')}, AC: {m.get('ac','-')}, Speed: {m.get('speed','-')}"
    )
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("К списку", callback_data="monster:list:page:1")]])
    await query.edit_message_text(text, reply_markup=markup)


async def monster_random(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    logger.info("Monster random requested", extra={"correlation_id": query.message.chat_id if query and query.message else None})
    all_monsters = await api_get("/monsters")
    if not all_monsters:
        logger.warning("No monsters available for random", extra={"correlation_id": query.message.chat_id if query and query.message else None})
        await query.edit_message_text("Монстров нет.")
        return
    m = random.choice(all_monsters)
    text = (
        f"{m.get('description','')}" + " (random)\n"
        f"Danger: {m.get('dangerous_lvl','-')}\n"
        f"HP: {m.get('hp','-')}, AC: {m.get('ac','-')}, Speed: {m.get('speed','-')}"
    )
    await query.edit_message_text(text)


async def monster_search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    context.user_data["awaiting_monster_query"] = True
    logger.info("Monster search prompt shown", extra={"correlation_id": query.message.chat_id if query and query.message else None})
    await query.edit_message_text("Введите подстроку для поиска по названию монстра:")


