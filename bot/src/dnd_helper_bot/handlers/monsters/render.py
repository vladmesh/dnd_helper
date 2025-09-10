from typing import Any, Dict, List, Optional, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
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
        try:
            await query.edit_message_text(
                await t("list.empty.monsters", lang, default=("No monsters." if lang == "en" else "Монстров нет.")),
                reply_markup=markup,
            )
        except BadRequest as e:
            if "Message is not modified" in str(e):
                await query.answer()
            else:
                raise
        else:
            await query.answer()
        return
    page_items = paginate(filtered, page)
    rows: List[List[InlineKeyboardButton]] = await _build_filters_keyboard(pending, lang, type_options, add_menu_open)
    for m in page_items:
        label = f"{m.get('name','')}"
        rows.append([InlineKeyboardButton(label, callback_data=f"monster:detail:{m['id']}")])
    nav: List[InlineKeyboardButton] = []
    if (page - 1) * 5 > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"monster:list:page:{page-1}"))
    if page * 5 < total:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"monster:list:page:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append(await _nav_row(lang, "menu:monsters"))
    markup = InlineKeyboardMarkup(rows)
    title = await t("list.title.monsters", lang)
    suffix = f" (p. {page})" if lang == "en" else f" (стр. {page})"
    try:
        await query.edit_message_text(title + suffix, reply_markup=markup)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            await query.answer()
        else:
            raise
    else:
        await query.answer()


async def _build_filters_keyboard(pending: Dict[str, Any], lang: str, type_options: List[Tuple[str, str]], add_menu_open: bool) -> List[List[InlineKeyboardButton]]:
    rows: List[List[InlineKeyboardButton]] = []

    # Manage row: Add | Reset
    add_lbl = await t("filters.add", lang)
    reset_lbl = await t("filters.reset", lang)
    rows.append([InlineKeyboardButton(add_lbl, callback_data="mflt:add"), InlineKeyboardButton(reset_lbl, callback_data="mflt:reset")])

    # Add submenu if open: list filters not visible
    all_fields = ["cr_buckets", "types", "sizes", "flying"]
    visible_fields = pending.get("visible_fields") or ["cr_buckets", "types"]
    if add_menu_open:
        available = [f for f in all_fields if f not in visible_fields]
        if available:
            fld_key = {
                "cr_buckets": "filters.field.cr",
                "types": "filters.field.type",
                "sizes": "filters.field.size",
                "flying": "filters.field.flying",
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
    yes_lbl = await t("filters.flying.yes", lang)
    no_lbl = await t("filters.flying.no", lang)
    remove_lbl = await t("filters.remove", lang)

    # Render each visible field in order
    for field in visible_fields:
        if field == "cr_buckets":
            cr_sel = pending.get("cr_buckets")
            any_base = any_lbl + " " + (await t("filters.field.cr", lang))
            any_txt = ("✅ " if cr_sel is None else "") + any_base
            # Row with Any only to avoid truncation
            rows.append([InlineKeyboardButton(any_txt, callback_data="mflt:cr:any")])
            # Row with bucket options
            cr03 = ("✅ " if isinstance(cr_sel, set) and "03" in cr_sel else "") + await t("filters.cr.03", lang)
            cr48 = ("✅ " if isinstance(cr_sel, set) and "48" in cr_sel else "") + await t("filters.cr.48", lang)
            cr9p = ("✅ " if isinstance(cr_sel, set) and "9p" in cr_sel else "") + await t("filters.cr.9p", lang)
            bucket_row = [
                InlineKeyboardButton(cr03, callback_data="mflt:cr:03"),
                InlineKeyboardButton(cr48, callback_data="mflt:cr:48"),
                InlineKeyboardButton(cr9p, callback_data="mflt:cr:9p"),
            ]
            rows.append(bucket_row)
            # Append Remove at end of the CR section
            if rows and len(rows[-1]) < 4:
                rows[-1].append(InlineKeyboardButton(remove_lbl, callback_data="mflt:rm:cr_buckets"))
            else:
                rows.append([InlineKeyboardButton(remove_lbl, callback_data="mflt:rm:cr_buckets")])
        elif field == "types":
            is_any_types = not isinstance(pending.get("types"), set)
            selected_types = pending.get("types") if isinstance(pending.get("types"), set) else None
            # Build buttons for each type with selection prefix
            type_buttons: List[InlineKeyboardButton] = []
            for code, label in type_options:
                prefix = "✅ " if isinstance(selected_types, set) and code in selected_types else ""
                type_buttons.append(InlineKeyboardButton(prefix + str(label), callback_data=f"mflt:type:{code}"))

            # First row: Any only to avoid truncation
            any_base = any_lbl + " " + (await t("filters.field.type", lang))
            any_txt = ("✅ " if is_any_types else "") + any_base
            rows.append([InlineKeyboardButton(any_txt, callback_data="mflt:type:any")])

            # Type buttons go in rows of up to 4
            remaining = type_buttons
            while remaining:
                rows.append(remaining[:4])
                remaining = remaining[4:]

            # Append Remove button at the end of the entire Types section
            if rows and len(rows[-1]) < 4:
                rows[-1].append(InlineKeyboardButton(remove_lbl, callback_data="mflt:rm:types"))
            else:
                rows.append([InlineKeyboardButton(remove_lbl, callback_data="mflt:rm:types")])
        elif field == "sizes":
            sz_sel = pending.get("sizes")
            any_base = any_lbl + " " + (await t("filters.field.size", lang))
            any_txt = ("✅ " if not isinstance(sz_sel, set) else "") + any_base
            # Row with Any only
            rows.append([InlineKeyboardButton(any_txt, callback_data="mflt:sz:any")])
            # Row with size options
            szS = ("✅ " if isinstance(sz_sel, set) and "S" in sz_sel else "") + await t("filters.size.S", lang)
            szM = ("✅ " if isinstance(sz_sel, set) and "M" in sz_sel else "") + await t("filters.size.M", lang)
            szL = ("✅ " if isinstance(sz_sel, set) and "L" in sz_sel else "") + await t("filters.size.L", lang)
            size_row = [
                InlineKeyboardButton(szS, callback_data="mflt:sz:S"),
                InlineKeyboardButton(szM, callback_data="mflt:sz:M"),
                InlineKeyboardButton(szL, callback_data="mflt:sz:L"),
            ]
            rows.append(size_row)
            # Append Remove at end of the Sizes section
            if rows and len(rows[-1]) < 4:
                rows[-1].append(InlineKeyboardButton(remove_lbl, callback_data="mflt:rm:sizes"))
            else:
                rows.append([InlineKeyboardButton(remove_lbl, callback_data="mflt:rm:sizes")])
        elif field == "flying":
            sel = pending.get("flying")
            row = [
                InlineKeyboardButton(("✅ " if sel is None else "") + any_lbl, callback_data="mflt:fly:any"),
                InlineKeyboardButton(("✅ " if sel is True else "") + yes_lbl, callback_data="mflt:fly:yes"),
                InlineKeyboardButton(("✅ " if sel is False else "") + no_lbl, callback_data="mflt:fly:no"),
                InlineKeyboardButton(remove_lbl, callback_data="mflt:rm:flying"),
            ]
            rows.append(row)
        

    return rows


