import logging
import random
from typing import Any, Dict, List, Optional, Tuple

from dnd_helper_bot.repositories.api_client import api_get, api_get_one
from dnd_helper_bot.utils.pagination import paginate
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


def _default_spells_filters() -> Dict[str, Any]:
    return {
        "ritual": None,  # None or True
        "is_concentration": None,  # None or True
        "cast": {"bonus": False, "reaction": False},
        "level_range": None,  # "13" | "45" | "69" | None
    }


def _get_filter_state(context: ContextTypes.DEFAULT_TYPE) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    user_data = context.user_data
    if "spells_filters_pending" not in user_data:
        user_data["spells_filters_pending"] = _default_spells_filters()
    if "spells_filters_applied" not in user_data:
        user_data["spells_filters_applied"] = _default_spells_filters()
    return user_data["spells_filters_pending"], user_data["spells_filters_applied"]


def _set_filter_state(context: ContextTypes.DEFAULT_TYPE, *, pending: Optional[Dict[str, Any]] = None, applied: Optional[Dict[str, Any]] = None) -> None:
    if pending is not None:
        context.user_data["spells_filters_pending"] = pending
    if applied is not None:
        context.user_data["spells_filters_applied"] = applied


def _toggle_or_set_filters(pending: Dict[str, Any], token: str) -> Dict[str, Any]:
    # token formats: rit | conc | ct:ba | ct:re | lv:13 | lv:45 | lv:69
    updated = {**pending, "cast": {**pending.get("cast", {})}}
    if token == "rit":
        updated["ritual"] = None if pending.get("ritual") else True
    elif token == "conc":
        updated["is_concentration"] = None if pending.get("is_concentration") else True
    elif token == "ct:ba":
        updated["cast"]["bonus"] = not pending.get("cast", {}).get("bonus", False)
    elif token == "ct:re":
        updated["cast"]["reaction"] = not pending.get("cast", {}).get("reaction", False)
    elif token.startswith("lv:"):
        val = token.split(":", 1)[1]
        updated["level_range"] = None if pending.get("level_range") == val else val
    return updated


def _filter_spells(items: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    def match_casting_time(value: Optional[str], want_bonus: bool, want_reaction: bool) -> bool:
        if not (want_bonus or want_reaction):
            return True
        if value is None:
            return False
        v = str(value).lower()
        bonus_ok = ("bonus_action" in v) or ("bonus action" in v)
        react_ok = "reaction" in v
        conds: List[bool] = []
        if want_bonus:
            conds.append(bonus_ok)
        if want_reaction:
            conds.append(react_ok)
        return all(conds)

    def level_in_range(level: Optional[int], rng: Optional[str]) -> bool:
        if rng is None:
            return True
        if level is None:
            return False
        if rng == "13":
            return 1 <= level <= 3
        if rng == "45":
            return 4 <= level <= 5
        if rng == "69":
            return 6 <= level <= 9
        return True

    result: List[Dict[str, Any]] = []
    for s in items:
        if filters.get("ritual") is True and not s.get("ritual", False):
            continue
        if filters.get("is_concentration") is True and not s.get("is_concentration", False):
            continue
        cast = filters.get("cast", {})
        if not match_casting_time(s.get("casting_time"), cast.get("bonus", False), cast.get("reaction", False)):
            continue
        if not level_in_range(s.get("level"), filters.get("level_range")):
            continue
        result.append(s)
    return result


def _build_filters_keyboard(pending: Dict[str, Any]) -> List[List[InlineKeyboardButton]]:
    rit = "✅ Ritual" if pending.get("ritual") else "Ritual"
    conc = "✅ Concentration" if pending.get("is_concentration") else "Concentration"
    bonus = "✅ Bonus" if pending.get("cast", {}).get("bonus") else "Bonus"
    react = "✅ Reaction" if pending.get("cast", {}).get("reaction") else "Reaction"
    lv = pending.get("level_range")
    lv13 = ("✅ Lv 1-3" if lv == "13" else "Lv 1-3")
    lv45 = ("✅ Lv 4-5" if lv == "45" else "Lv 4-5")
    lv69 = ("✅ Lv 6-9" if lv == "69" else "Lv 6-9")
    return [
        [InlineKeyboardButton(rit, callback_data="sflt:rit"), InlineKeyboardButton(conc, callback_data="sflt:conc")],
        [InlineKeyboardButton(bonus, callback_data="sflt:ct:ba"), InlineKeyboardButton(react, callback_data="sflt:ct:re")],
        [InlineKeyboardButton(lv13, callback_data="sflt:lv:13"), InlineKeyboardButton(lv45, callback_data="sflt:lv:45"), InlineKeyboardButton(lv69, callback_data="sflt:lv:69")],
        [InlineKeyboardButton("Apply", callback_data="sflt:apply"), InlineKeyboardButton("Reset", callback_data="sflt:reset")],
    ]


async def _render_spells_list(query, context: ContextTypes.DEFAULT_TYPE, page: int) -> None:
    context.user_data["spells_current_page"] = page
    pending, applied = _get_filter_state(context)
    all_spells: List[Dict[str, Any]] = await api_get("/spells")
    filtered = _filter_spells(all_spells, applied)
    total = len(filtered)
    if total == 0:
        rows: List[List[InlineKeyboardButton]] = _build_filters_keyboard(pending)
        markup = InlineKeyboardMarkup(rows)
        await query.edit_message_text("Заклинаний нет.", reply_markup=markup)
        return
    page_items = paginate(filtered, page)
    rows: List[List[InlineKeyboardButton]] = _build_filters_keyboard(pending)
    for s in page_items:
        label = f"Подробнее: {s.get('name','')} (#{s.get('id')})"
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


async def spells_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    page = int(query.data.split(":")[-1])
    logger.info("Spells list requested", extra={"correlation_id": query.message.chat_id if query and query.message else None, "page": page})
    await _render_spells_list(query, context, page)


async def spell_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    spell_id = int(query.data.split(":")[-1])
    logger.info("Spell detail requested", extra={"correlation_id": query.message.chat_id if query and query.message else None, "spell_id": spell_id})
    s = await api_get_one(f"/spells/{spell_id}")
    classes = s.get("classes") or []
    classes_str = ", ".join(classes) if isinstance(classes, list) else str(classes or "-")
    text = (
        f"{s.get('name','-')}\n"
        f"{s.get('description','')}\n"
        f"Classes: {classes_str}\n"
        f"School: {s.get('school','-')}"
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
    classes = s.get("classes") or []
    classes_str = ", ".join(classes) if isinstance(classes, list) else str(classes or "-")
    text = (
        f"{s.get('description','')}" + " (random)\n"
        f"Classes: {classes_str}\n"
        f"School: {s.get('school','-')}"
    )
    await query.edit_message_text(text)


async def spell_search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    context.user_data["awaiting_spell_query"] = True
    logger.info("Spell search prompt shown", extra={"correlation_id": query.message.chat_id if query and query.message else None})
    await query.edit_message_text("Введите подстроку для поиска по названию заклинания:")


async def spells_filter_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data  # e.g., sflt:rit, sflt:apply, sflt:reset
    logger.info("Spells filter action", extra={
        "correlation_id": query.message.chat_id if query and query.message else None,
        "action": data,
    })
    pending, applied = _get_filter_state(context)
    token = data.split(":", 1)[1]
    if token == "apply":
        _set_filter_state(context, applied={**pending, "cast": {**pending.get("cast", {})}})
        page = 1
    elif token == "reset":
        _set_filter_state(context, pending=_default_spells_filters(), applied=_default_spells_filters())
        page = 1
    else:
        new_pending = _toggle_or_set_filters(pending, token)
        _set_filter_state(context, pending=new_pending)
        page = int(context.user_data.get("spells_current_page", 1))

    await _render_spells_list(query, context, page)


