import logging
import random
from typing import Any, Dict, List, Optional, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from dnd_helper_bot.repositories.api_client import api_get, api_get_one
from dnd_helper_bot.utils.pagination import paginate
from dnd_helper_bot.utils.i18n import t
from dnd_helper_bot.utils.nav import build_nav_row
from .spells import *  # type: ignore  # re-export for backward compatibility

logger = logging.getLogger(__name__)


async def _resolve_lang_by_user(update_or_query) -> str:
    """Prefer DB user's language; fallback to Telegram UI language."""
    try:
        tg_user = None
        if hasattr(update_or_query, "effective_user") and update_or_query.effective_user is not None:
            tg_user = update_or_query.effective_user
        elif hasattr(update_or_query, "from_user") and update_or_query.from_user is not None:
            tg_user = update_or_query.from_user
        tg_id = getattr(tg_user, "id", None)
        if tg_id is not None:
            user = await api_get_one(f"/users/by-telegram/{tg_id}")
            lang = user.get("lang")
            if lang in ("ru", "en"):
                return lang
    except Exception:
        pass
    try:
        code = None
        if hasattr(update_or_query, "effective_user") and update_or_query.effective_user is not None:
            code = (update_or_query.effective_user.language_code or "ru").lower()
        elif hasattr(update_or_query, "from_user") and update_or_query.from_user is not None:
            code = (update_or_query.from_user.language_code or "ru").lower()
        return "en" if str(code).startswith("en") else "ru"
    except Exception:
        return "ru"


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


def _build_filters_keyboard(pending: Dict[str, Any], lang: str) -> List[List[InlineKeyboardButton]]:
    def _tt(en: str, ru: str) -> str:
        return en if lang == "en" else ru

    rit = ("✅ " if pending.get("ritual") else "") + _tt("Ritual", "Ритуал")
    conc = ("✅ " if pending.get("is_concentration") else "") + _tt("Concentration", "Концентрация")
    bonus = ("✅ " if pending.get("cast", {}).get("bonus") else "") + _tt("Bonus", "Бонус")
    react = ("✅ " if pending.get("cast", {}).get("reaction") else "") + _tt("Reaction", "Реакция")
    lv = pending.get("level_range")
    lv13 = ("✅ " if lv == "13" else "") + _tt("Lv 1-3", "Ур 1-3")
    lv45 = ("✅ " if lv == "45" else "") + _tt("Lv 4-5", "Ур 4-5")
    lv69 = ("✅ " if lv == "69" else "") + _tt("Lv 6-9", "Ур 6-9")
    apply = _tt("Apply", "Применить")
    reset = _tt("Reset", "Сброс")
    return [
        [InlineKeyboardButton(rit, callback_data="sflt:rit"), InlineKeyboardButton(conc, callback_data="sflt:conc")],
        [InlineKeyboardButton(bonus, callback_data="sflt:ct:ba"), InlineKeyboardButton(react, callback_data="sflt:ct:re")],
        [InlineKeyboardButton(lv13, callback_data="sflt:lv:13"), InlineKeyboardButton(lv45, callback_data="sflt:lv:45"), InlineKeyboardButton(lv69, callback_data="sflt:lv:69")],
        [InlineKeyboardButton(apply, callback_data="sflt:apply"), InlineKeyboardButton(reset, callback_data="sflt:reset")],
    ]


async def _detect_lang(update_or_query) -> str:
    # Deprecated: kept for compatibility
    try:
        user_lang = (update_or_query.effective_user.language_code or "ru").lower()
        return "en" if user_lang.startswith("en") else "ru"
    except Exception:
        return "ru"


async def _nav_row(lang: str, back_callback: str) -> list[InlineKeyboardButton]:
    return await build_nav_row(lang, back_callback)


async def _render_spells_list(query, context: ContextTypes.DEFAULT_TYPE, page: int) -> None:
    context.user_data["spells_current_page"] = page
    pending, applied = _get_filter_state(context)
    lang = await _resolve_lang_by_user(query)
    wrapped_list: List[Dict[str, Any]] = await api_get("/spells/wrapped", params={"lang": lang})

    # Flatten for filtering/listing
    all_spells: List[Dict[str, Any]] = []
    for w in wrapped_list:
        e = (w.get("entity") or {})
        t = (w.get("translation") or {})
        all_spells.append(
            {
                "id": e.get("id"),
                "name": t.get("name") or "",
                "description": t.get("description") or "",
                "ritual": e.get("ritual"),
                "is_concentration": e.get("is_concentration"),
                "casting_time": e.get("casting_time"),
                "level": e.get("level"),
            }
        )

    filtered = _filter_spells(all_spells, applied)
    total = len(filtered)
    if total == 0:
        rows: List[List[InlineKeyboardButton]] = _build_filters_keyboard(pending, lang)
        markup = InlineKeyboardMarkup(rows)
        await query.edit_message_text(await t("list.empty.spells", lang, default=("No spells." if lang == "en" else "Заклинаний нет.")), reply_markup=markup)
        return
    page_items = paginate(filtered, page)
    rows: List[List[InlineKeyboardButton]] = _build_filters_keyboard(pending, lang)
    for s in page_items:
        more = ("More:" if lang == "en" else "Подробнее:")
        label = f"{more} {s.get('name','')} (#{s.get('id')})"
        rows.append([InlineKeyboardButton(label, callback_data=f"spell:detail:{s['id']}")])
    nav: List[InlineKeyboardButton] = []
    if (page - 1) * 5 > 0:
        nav.append(InlineKeyboardButton((await t("nav.back", lang, default=("⬅️ Back" if lang == "en" else "⬅️ Назад"))), callback_data=f"spell:list:page:{page-1}"))
    if page * 5 < total:
        nav.append(InlineKeyboardButton((await t("nav.next", lang, default=("➡️ Next" if lang == "en" else "➡️ Далее"))), callback_data=f"spell:list:page:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append(await _nav_row(lang, "menu:spells"))
    markup = InlineKeyboardMarkup(rows)
    await query.edit_message_text((f"Spells list (p. {page})" if lang == "en" else f"Список заклинаний (стр. {page})"), reply_markup=markup)


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
    lang = await _resolve_lang_by_user(query)
    w = await api_get_one(f"/spells/{spell_id}/wrapped", params={"lang": lang})
    e = w.get("entity") or {}
    t = w.get("translation") or {}
    labels = w.get("labels") or {}
    classes_l = labels.get("classes") or []
    classes_str = ", ".join([(c.get("label") or c.get("code")) for c in classes_l]) if classes_l else "-"
    school_l = labels.get("school") or {}
    school_str = school_l.get("label") if isinstance(school_l, dict) else (e.get("school") or "-")
    text = (
        f"{t.get('name','-')}\n"
        f"{t.get('description','')}\n"
        f"{('Classes' if lang == 'en' else 'Классы')}: {classes_str}\n"
        f"{('School' if lang == 'en' else 'Школа')}: {school_str}"
    )
    page = int(context.user_data.get("spells_current_page", 1))
    markup = InlineKeyboardMarkup([await _nav_row(lang, f"spell:list:page:{page}")])
    await query.edit_message_text(text, reply_markup=markup)


async def spell_random(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    logger.info("Spell random requested", extra={"correlation_id": query.message.chat_id if query and query.message else None})
    lang = await _resolve_lang_by_user(query)
    wrapped_list = await api_get("/spells/wrapped", params={"lang": lang})
    if not wrapped_list:
        logger.warning("No spells available for random", extra={"correlation_id": query.message.chat_id if query and query.message else None})
        await query.edit_message_text(await t("list.empty.spells", lang, default="Заклинаний нет."))
        return
    w = random.choice(wrapped_list)
    e = w.get("entity") or {}
    t = w.get("translation") or {}
    labels = w.get("labels") or {}
    classes_l = labels.get("classes") or []
    classes_str = ", ".join([(c.get("label") or c.get("code")) for c in classes_l]) if classes_l else "-"
    school_l = labels.get("school") or {}
    school_str = school_l.get("label") if isinstance(school_l, dict) else (e.get("school") or "-")
    text = (
        f"{t.get('description','')}"
        + (" (random)\n" if lang == "en" else " (случайно)\n")
        + f"{('Classes' if lang == 'en' else 'Классы')}: {classes_str}\n"
        + f"{('School' if lang == 'en' else 'Школа')}: {school_str}"
    )
    markup = InlineKeyboardMarkup([await _nav_row(lang, "menu:spells")])
    await query.edit_message_text(text, reply_markup=markup)


async def spell_search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    context.user_data["awaiting_spell_query"] = True
    logger.info("Spell search prompt shown", extra={"correlation_id": query.message.chat_id if query and query.message else None})
    lang = await _resolve_lang_by_user(query)
    markup = InlineKeyboardMarkup([await _nav_row(lang, "menu:spells")])
    await query.edit_message_text(await t("spells.search.prompt", lang, default="Введите подстроку для поиска по названию заклинания:"), reply_markup=markup)


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


