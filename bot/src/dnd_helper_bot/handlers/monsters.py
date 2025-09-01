import logging
import random
from typing import Any, Dict, List, Optional, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from dnd_helper_bot.repositories.api_client import api_get, api_get_one
from dnd_helper_bot.utils.pagination import paginate

logger = logging.getLogger(__name__)


def _default_monsters_filters() -> Dict[str, Any]:
    return {
        "legendary": None,  # None or True
        "flying": None,  # None or True
        "cr_range": None,  # "03" | "48" | "9p" | None
        "size": None,  # "S" | "M" | "L" | None
    }


def _get_filter_state(context: ContextTypes.DEFAULT_TYPE) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    user_data = context.user_data
    if "monsters_filters_pending" not in user_data:
        user_data["monsters_filters_pending"] = _default_monsters_filters()
    if "monsters_filters_applied" not in user_data:
        user_data["monsters_filters_applied"] = _default_monsters_filters()
    return user_data["monsters_filters_pending"], user_data["monsters_filters_applied"]


def _set_filter_state(context: ContextTypes.DEFAULT_TYPE, *, pending: Optional[Dict[str, Any]] = None, applied: Optional[Dict[str, Any]] = None) -> None:
    if pending is not None:
        context.user_data["monsters_filters_pending"] = pending
    if applied is not None:
        context.user_data["monsters_filters_applied"] = applied


def _toggle_or_set_filters(pending: Dict[str, Any], token: str) -> Dict[str, Any]:
    # token formats: leg | fly | cr:03|48|9p | sz:S|M|L
    updated = dict(pending)
    if token == "leg":
        updated["legendary"] = None if pending.get("legendary") else True
    elif token == "fly":
        updated["flying"] = None if pending.get("flying") else True
    elif token.startswith("cr:"):
        val = token.split(":", 1)[1]
        updated["cr_range"] = None if pending.get("cr_range") == val else val
    elif token.startswith("sz:"):
        val = token.split(":", 1)[1]
        updated["size"] = None if pending.get("size") == val else val
    return updated


def _filter_monsters(items: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    def cr_in_range(cr_value: Optional[float], rng: Optional[str]) -> bool:
        if rng is None:
            return True
        if cr_value is None:
            return False
        if rng == "03":
            return 0 <= cr_value <= 3
        if rng == "48":
            return 4 <= cr_value <= 8
        if rng == "9p":
            return cr_value >= 9
        return True

    result: List[Dict[str, Any]] = []
    for m in items:
        if filters.get("legendary") is True and not m.get("is_legendary", False):
            continue
        if filters.get("flying") is True and not m.get("is_flying", False):
            continue
        if not cr_in_range(m.get("cr"), filters.get("cr_range")):
            continue
        size = filters.get("size")
        if size is not None and m.get("size") != size:
            continue
        result.append(m)
    return result


def _build_filters_keyboard(pending: Dict[str, Any]) -> List[List[InlineKeyboardButton]]:
    leg = "✅ Legendary" if pending.get("legendary") else "Legendary"
    fly = "✅ Flying" if pending.get("flying") else "Flying"
    cr = pending.get("cr_range")
    cr03 = ("✅ CR 0-3" if cr == "03" else "CR 0-3")
    cr48 = ("✅ CR 4-8" if cr == "48" else "CR 4-8")
    cr9p = ("✅ CR 9+" if cr == "9p" else "CR 9+")
    sz = pending.get("size")
    szS = ("✅ Size S" if sz == "S" else "Size S")
    szM = ("✅ Size M" if sz == "M" else "Size M")
    szL = ("✅ Size L" if sz == "L" else "Size L")
    return [
        [InlineKeyboardButton(leg, callback_data="mflt:leg"), InlineKeyboardButton(fly, callback_data="mflt:fly")],
        [InlineKeyboardButton(cr03, callback_data="mflt:cr:03"), InlineKeyboardButton(cr48, callback_data="mflt:cr:48"), InlineKeyboardButton(cr9p, callback_data="mflt:cr:9p")],
        [InlineKeyboardButton(szS, callback_data="mflt:sz:S"), InlineKeyboardButton(szM, callback_data="mflt:sz:M"), InlineKeyboardButton(szL, callback_data="mflt:sz:L")],
        [InlineKeyboardButton("Apply", callback_data="mflt:apply"), InlineKeyboardButton("Reset", callback_data="mflt:reset")],
    ]


async def _render_monsters_list(query, context: ContextTypes.DEFAULT_TYPE, page: int) -> None:
    context.user_data["monsters_current_page"] = page
    pending, applied = _get_filter_state(context)
    all_monsters: List[Dict[str, Any]] = await api_get("/monsters")
    filtered = _filter_monsters(all_monsters, applied)
    total = len(filtered)
    if total == 0:
        rows: List[List[InlineKeyboardButton]] = _build_filters_keyboard(pending)
        markup = InlineKeyboardMarkup(rows)
        await query.edit_message_text("Монстров нет.", reply_markup=markup)
        return
    page_items = paginate(filtered, page)
    rows: List[List[InlineKeyboardButton]] = _build_filters_keyboard(pending)
    for m in page_items:
        label = f"{m.get('name','')} (#{m.get('id')})"
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


async def monsters_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    page = int(query.data.split(":")[-1])
    logger.info("Monsters list requested", extra={"correlation_id": query.message.chat_id if query and query.message else None, "page": page})
    await _render_monsters_list(query, context, page)


async def monster_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    monster_id = int(query.data.split(":")[-1])
    logger.info("Monster detail requested", extra={"correlation_id": query.message.chat_id if query and query.message else None, "monster_id": monster_id})
    m = await api_get_one(f"/monsters/{monster_id}")
    danger_text = m.get('cr') or m.get('cr_enum') or m.get('dangerous_lvl', '-')
    text = (
        f"{m.get('name','-')}\n"
        f"{m.get('description','')}\n"
        f"CR: {danger_text}\n"
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
    danger_text = m.get('cr') or m.get('cr_enum') or m.get('dangerous_lvl', '-')
    text = (
        f"{m.get('description','')}" + " (random)\n"
        f"CR: {danger_text}\n"
        f"HP: {m.get('hp','-')}, AC: {m.get('ac','-')}, Speed: {m.get('speed','-')}"
    )
    await query.edit_message_text(text)


async def monster_search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    context.user_data["awaiting_monster_query"] = True
    logger.info("Monster search prompt shown", extra={"correlation_id": query.message.chat_id if query and query.message else None})
    await query.edit_message_text("Введите подстроку для поиска по названию монстра:")


async def monsters_filter_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data  # e.g., mflt:leg, mflt:apply, mflt:reset
    logger.info("Monsters filter action", extra={
        "correlation_id": query.message.chat_id if query and query.message else None,
        "action": data,
    })
    pending, applied = _get_filter_state(context)
    token = data.split(":", 1)[1]
    if token == "apply":
        _set_filter_state(context, applied=dict(pending))
        page = 1
    elif token == "reset":
        _set_filter_state(context, pending=_default_monsters_filters(), applied=_default_monsters_filters())
        page = 1
    else:
        new_pending = _toggle_or_set_filters(pending, token)
        _set_filter_state(context, pending=new_pending)
        page = int(context.user_data.get("monsters_current_page", 1))

    await _render_monsters_list(query, context, page)


