from typing import Any, Dict, List, Optional, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from dnd_helper_bot.repositories.api_client import api_get
from dnd_helper_bot.utils.i18n import t
from dnd_helper_bot.utils.nav import build_nav_row
from dnd_helper_bot.utils.pagination import paginate

from .filters import _filter_monsters, _get_filter_state
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
    wrapped_list: List[Dict[str, Any]] = await api_get("/monsters/list/wrapped", params={"lang": lang})

    all_monsters: List[Dict[str, Any]] = []
    type_map: Dict[str, str] = {}
    for w in wrapped_list:
        e = w.get("entity") or {}
        t_tr = w.get("translation") or {}
        lbls = w.get("labels") or {}
        t_label = None
        t_code = None
        if isinstance(lbls, dict):
            t_info = lbls.get("type")
            if isinstance(t_info, dict):
                t_code = (t_info.get("code") or "").strip().lower() or None
                t_label = t_info.get("label") or None
        if not t_code:
            v = e.get("type")
            t_code = (str(v).strip().lower() if v is not None else None) or None
        if t_code and isinstance(t_label, str):
            type_map.setdefault(t_code, t_label)
        all_monsters.append(
            {
                "id": e.get("id"),
                "name": t_tr.get("name") or "",
                "description": t_tr.get("description") or "",
                "is_legendary": e.get("is_legendary"),
                "is_flying": e.get("is_flying"),
                "cr": _cr_to_float(e.get("cr")),
                "size": _size_letter(e.get("size")),
                "type": t_code,
            }
        )

    filtered = _filter_monsters(all_monsters, applied)
    total = len(filtered)
    # Prepare type options for keyboard (sorted by label)
    type_options: List[Tuple[str, str]] = sorted(type_map.items(), key=lambda x: (x[1] or ""))
    if total == 0:
        rows: List[List[InlineKeyboardButton]] = await _build_filters_keyboard(pending, lang, type_options)
        markup = InlineKeyboardMarkup(rows)
        await query.edit_message_text(
            await t("list.empty.monsters", lang, default=("No monsters." if lang == "en" else "Монстров нет.")),
            reply_markup=markup,
        )
        return
    page_items = paginate(filtered, page)
    rows: List[List[InlineKeyboardButton]] = await _build_filters_keyboard(pending, lang, type_options)
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


async def _build_filters_keyboard(pending: Dict[str, Any], lang: str, type_options: List[Tuple[str, str]]) -> List[List[InlineKeyboardButton]]:
    rows: List[List[InlineKeyboardButton]] = []
    # CR buckets row with Any + multi-select
    any_lbl = await t("filters.any", lang)
    cr_any_btn = InlineKeyboardButton(any_lbl, callback_data="mflt:cr:any")
    cr_sel = pending.get("cr_buckets")
    cr03 = ("✅ " if isinstance(cr_sel, set) and "03" in cr_sel else "") + await t("filters.cr.03", lang)
    cr48 = ("✅ " if isinstance(cr_sel, set) and "48" in cr_sel else "") + await t("filters.cr.48", lang)
    cr9p = ("✅ " if isinstance(cr_sel, set) and "9p" in cr_sel else "") + await t("filters.cr.9p", lang)
    rows.append([cr_any_btn, InlineKeyboardButton(cr03, callback_data="mflt:cr:03"), InlineKeyboardButton(cr48, callback_data="mflt:cr:48"), InlineKeyboardButton(cr9p, callback_data="mflt:cr:9p")])

    # Type row: Any + options (possibly split into multiple rows if many)
    type_any_btn = InlineKeyboardButton(any_lbl, callback_data="mflt:type:any")
    selected_types = pending.get("types") if isinstance(pending.get("types"), set) else None
    type_buttons: List[InlineKeyboardButton] = []
    for code, label in type_options:
        prefix = "✅ " if isinstance(selected_types, set) and code in selected_types else ""
        type_buttons.append(InlineKeyboardButton(prefix + str(label), callback_data=f"mflt:type:{code}"))
    # Build rows: first row starts with Any, then some buttons; subsequent rows contain remaining buttons
    first_row: List[InlineKeyboardButton] = [type_any_btn]
    # Distribute up to 3 per row after the first slot to keep width reasonable
    for btn in type_buttons[:3]:
        first_row.append(btn)
    rows.append(first_row)
    remaining = type_buttons[3:]
    while remaining:
        rows.append(remaining[:4])
        remaining = remaining[4:]

    reset = await t("filters.reset", lang)
    rows.append([InlineKeyboardButton(reset, callback_data="mflt:reset")])
    return rows


