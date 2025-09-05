from typing import Any, Dict, List, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from dnd_helper_bot.repositories.api_client import api_get
from dnd_helper_bot.utils.pagination import paginate
from dnd_helper_bot.utils.i18n import t
from dnd_helper_bot.utils.nav import build_nav_row

from .filters import _get_filter_state, _filter_monsters
from .lang import _resolve_lang_by_user


async def _nav_row(lang: str, back_callback: str) -> list[InlineKeyboardButton]:
    return await build_nav_row(lang, back_callback)


def _cr_to_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        s = str(value)
        if "/" in s:
            a, b = s.split("/", 1)
            return float(a) / float(b)
        return float(s)
    except Exception:
        return None


def _size_letter(code: Optional[str]) -> Optional[str]:
    m = {"tiny": "S", "small": "S", "medium": "M", "large": "L", "huge": "L", "gargantuan": "L"}
    return m.get(str(code).lower()) if code else None


async def render_monsters_list(query, context: ContextTypes.DEFAULT_TYPE, page: int) -> None:
    context.user_data["monsters_current_page"] = page
    pending, applied = _get_filter_state(context)
    lang = await _resolve_lang_by_user(query)
    wrapped_list: List[Dict[str, Any]] = await api_get("/monsters/wrapped-list", params={"lang": lang})

    all_monsters: List[Dict[str, Any]] = []
    for w in wrapped_list:
        e = w.get("entity") or {}
        t_tr = w.get("translation") or {}
        all_monsters.append(
            {
                "id": e.get("id"),
                "name": t_tr.get("name") or "",
                "description": t_tr.get("description") or "",
                "is_legendary": e.get("is_legendary"),
                "is_flying": e.get("is_flying"),
                "cr": _cr_to_float(e.get("cr")),
                "size": _size_letter(e.get("size")),
            }
        )

    filtered = _filter_monsters(all_monsters, applied)
    total = len(filtered)
    if total == 0:
        rows: List[List[InlineKeyboardButton]] = await _build_filters_keyboard(pending, lang)
        markup = InlineKeyboardMarkup(rows)
        await query.edit_message_text(
            await t("list.empty.monsters", lang, default=("No monsters." if lang == "en" else "Монстров нет.")),
            reply_markup=markup,
        )
        return
    page_items = paginate(filtered, page)
    rows: List[List[InlineKeyboardButton]] = await _build_filters_keyboard(pending, lang)
    for m in page_items:
        label = f"{m.get('name','')} (#{m.get('id')})"
        rows.append([InlineKeyboardButton(label, callback_data=f"monster:detail:{m['id']}")])
    nav: List[InlineKeyboardButton] = []
    if (page - 1) * 5 > 0:
        nav.append(InlineKeyboardButton((await t("nav.back", lang)), callback_data=f"monster:list:page:{page-1}"))
    if page * 5 < total:
        nav.append(InlineKeyboardButton((await t("nav.next", lang)), callback_data=f"monster:list:page:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append(await _nav_row(lang, "menu:monsters"))
    markup = InlineKeyboardMarkup(rows)
    title = await t("list.title.monsters", lang)
    suffix = f" (p. {page})" if lang == "en" else f" (стр. {page})"
    await query.edit_message_text(title + suffix, reply_markup=markup)


async def _build_filters_keyboard(pending: Dict[str, Any], lang: str) -> List[List[InlineKeyboardButton]]:
    leg = ("✅ " if pending.get("legendary") else "") + await t("filters.legendary", lang)
    fly = ("✅ " if pending.get("flying") else "") + await t("filters.flying", lang)
    cr = pending.get("cr_range")
    cr03 = ("✅ " if cr == "03" else "") + await t("filters.cr.03", lang)
    cr48 = ("✅ " if cr == "48" else "") + await t("filters.cr.48", lang)
    cr9p = ("✅ " if cr == "9p" else "") + await t("filters.cr.9p", lang)
    sz = pending.get("size")
    szS = ("✅ " if sz == "S" else "") + await t("filters.size.S", lang)
    szM = ("✅ " if sz == "M" else "") + await t("filters.size.M", lang)
    szL = ("✅ " if sz == "L" else "") + await t("filters.size.L", lang)
    apply = await t("filters.apply", lang)
    reset = await t("filters.reset", lang)
    return [
        [InlineKeyboardButton(leg, callback_data="mflt:leg"), InlineKeyboardButton(fly, callback_data="mflt:fly")],
        [InlineKeyboardButton(cr03, callback_data="mflt:cr:03"), InlineKeyboardButton(cr48, callback_data="mflt:cr:48"), InlineKeyboardButton(cr9p, callback_data="mflt:cr:9p")],
        [InlineKeyboardButton(szS, callback_data="mflt:sz:S"), InlineKeyboardButton(szM, callback_data="mflt:sz:M"), InlineKeyboardButton(szL, callback_data="mflt:sz:L")],
        [InlineKeyboardButton(apply, callback_data="mflt:apply"), InlineKeyboardButton(reset, callback_data="mflt:reset")],
    ]


