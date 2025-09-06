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
    add_menu_open = bool(context.user_data.get("monsters_add_menu_open"))
    if total == 0:
        rows: List[List[InlineKeyboardButton]] = await _build_filters_keyboard(pending, lang, type_options, add_menu_open)
        markup = InlineKeyboardMarkup(rows)
        await query.edit_message_text(
            await t("list.empty.monsters", lang, default=("No monsters." if lang == "en" else "Монстров нет.")),
            reply_markup=markup,
        )
        return
    page_items = paginate(filtered, page)
    rows: List[List[InlineKeyboardButton]] = await _build_filters_keyboard(pending, lang, type_options, add_menu_open)
    for m in page_items:
        label = f"{m.get('name','')}"
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


async def _build_filters_keyboard(pending: Dict[str, Any], lang: str, type_options: List[Tuple[str, str]], add_menu_open: bool) -> List[List[InlineKeyboardButton]]:
    rows: List[List[InlineKeyboardButton]] = []

    # Manage row: Add | Reset
    add_lbl = await t("filters.add", lang)
    reset_lbl = await t("filters.reset", lang)
    rows.append([InlineKeyboardButton(add_lbl, callback_data="mflt:add"), InlineKeyboardButton(reset_lbl, callback_data="mflt:reset")])

    # Add submenu if open: list filters not visible
    all_fields = ["cr_buckets", "types", "sizes", "flying", "legendary"]
    visible_fields = pending.get("visible_fields") or ["cr_buckets", "types"]
    if add_menu_open:
        available = [f for f in all_fields if f not in visible_fields]
        if available:
            fld_key = {
                "cr_buckets": "filters.field.cr",
                "types": "filters.field.type",
                "sizes": "filters.field.size",
                "flying": "filters.field.flying",
                "legendary": "filters.field.legendary",
            }
            btns: List[InlineKeyboardButton] = []
            for f in available:
                label = await t(fld_key.get(f, f), lang)
                btns.append(InlineKeyboardButton(label, callback_data=f"mflt:add:{f}"))
            # pack 3-4 per row
            while btns:
                rows.append(btns[:4])
                btns = btns[4:]

    # Helper labels
    any_lbl = await t("filters.any", lang)
    yes_lbl = await t("filters.yes", lang)
    no_lbl = await t("filters.no", lang)
    remove_lbl = await t("filters.remove", lang)

    # Render each visible field in order
    for field in visible_fields:
        if field == "cr_buckets":
            cr_sel = pending.get("cr_buckets")
            row = [InlineKeyboardButton(any_lbl, callback_data="mflt:cr:any")]
            cr03 = ("✅ " if isinstance(cr_sel, set) and "03" in cr_sel else "") + await t("filters.cr.03", lang)
            cr48 = ("✅ " if isinstance(cr_sel, set) and "48" in cr_sel else "") + await t("filters.cr.48", lang)
            cr9p = ("✅ " if isinstance(cr_sel, set) and "9p" in cr_sel else "") + await t("filters.cr.9p", lang)
            row.extend([
                InlineKeyboardButton(cr03, callback_data="mflt:cr:03"),
                InlineKeyboardButton(cr48, callback_data="mflt:cr:48"),
                InlineKeyboardButton(cr9p, callback_data="mflt:cr:9p"),
            ])
            row.append(InlineKeyboardButton(remove_lbl, callback_data="mflt:rm:cr_buckets"))
            rows.append(row)
        elif field == "types":
            selected_types = pending.get("types") if isinstance(pending.get("types"), set) else None
            first_row: List[InlineKeyboardButton] = [InlineKeyboardButton(any_lbl, callback_data="mflt:type:any")]
            type_buttons: List[InlineKeyboardButton] = []
            for code, label in type_options:
                prefix = "✅ " if isinstance(selected_types, set) and code in selected_types else ""
                type_buttons.append(InlineKeyboardButton(prefix + str(label), callback_data=f"mflt:type:{code}"))
            for btn in type_buttons[:3]:
                first_row.append(btn)
            first_row.append(InlineKeyboardButton(remove_lbl, callback_data="mflt:rm:types"))
            rows.append(first_row)
            remaining = type_buttons[3:]
            while remaining:
                rows.append(remaining[:4])
                remaining = remaining[4:]
        elif field == "sizes":
            sz_sel = pending.get("sizes")
            row = [InlineKeyboardButton(any_lbl, callback_data="mflt:sz:any")]
            szS = ("✅ " if isinstance(sz_sel, set) and "S" in sz_sel else "") + await t("filters.size.S", lang)
            szM = ("✅ " if isinstance(sz_sel, set) and "M" in sz_sel else "") + await t("filters.size.M", lang)
            szL = ("✅ " if isinstance(sz_sel, set) and "L" in sz_sel else "") + await t("filters.size.L", lang)
            row.extend([
                InlineKeyboardButton(szS, callback_data="mflt:sz:S"),
                InlineKeyboardButton(szM, callback_data="mflt:sz:M"),
                InlineKeyboardButton(szL, callback_data="mflt:sz:L"),
            ])
            row.append(InlineKeyboardButton(remove_lbl, callback_data="mflt:rm:sizes"))
            rows.append(row)
        elif field == "flying":
            sel = pending.get("flying")
            row = [
                InlineKeyboardButton(any_lbl, callback_data="mflt:fly:any"),
                InlineKeyboardButton(("✅ " if sel is True else "") + yes_lbl, callback_data="mflt:fly:yes"),
                InlineKeyboardButton(("✅ " if sel is False else "") + no_lbl, callback_data="mflt:fly:no"),
                InlineKeyboardButton(remove_lbl, callback_data="mflt:rm:flying"),
            ]
            rows.append(row)
        elif field == "legendary":
            sel = pending.get("legendary")
            row = [
                InlineKeyboardButton(any_lbl, callback_data="mflt:leg:any"),
                InlineKeyboardButton(("✅ " if sel is True else "") + yes_lbl, callback_data="mflt:leg:yes"),
                InlineKeyboardButton(("✅ " if sel is False else "") + no_lbl, callback_data="mflt:leg:no"),
                InlineKeyboardButton(remove_lbl, callback_data="mflt:rm:legendary"),
            ]
            rows.append(row)

    return rows


