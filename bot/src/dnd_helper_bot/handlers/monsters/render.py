from typing import Any, Dict, List, Optional, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from dnd_helper_bot.repositories.api_client import api_get
from dnd_helper_bot.utils.i18n import t
from dnd_helper_bot.utils.nav import build_nav_row
from dnd_helper_bot.utils.pagination import paginate, PAGE_SIZE_LIST

from .filters import _filter_monsters, _get_filter_state
from .lang import _resolve_lang_by_user


async def _nav_row(lang: str, back_callback: str) -> list[InlineKeyboardButton]:
    return await build_nav_row(lang, back_callback)


async def _build_filters_header(
    applied: Dict[str, Any],
    lang: str,
    type_options: List[Tuple[str, str]],
) -> str:
    # If nothing applied -> "All monsters"
    has_any = False
    fields = ("cr_buckets", "cr_range", "types", "sizes", "size", "flying", "legendary")
    for f in fields:
        v = applied.get(f)
        if isinstance(v, set) and v:
            has_any = True
            break
        if v not in (None, False):
            if v is True or (isinstance(v, str) and v.strip() != ""):
                has_any = True
                break
    if not has_any:
        default_text = "All monsters" if lang == "en" else "Все монстры"
        return await t("list.all.monsters", lang, default=default_text)

    parts: List[str] = []
    # CR buckets
    cr_labels: List[str] = []
    cr_buckets = applied.get("cr_buckets")
    if isinstance(cr_buckets, set) and cr_buckets:
        code_to_key = {"03": "filters.cr.03", "48": "filters.cr.48", "9p": "filters.cr.9p"}
        for code in ("03", "48", "9p"):
            if code in cr_buckets:
                cr_labels.append(await t(code_to_key[code], lang))
    else:
        legacy = applied.get("cr_range")
        if isinstance(legacy, str) and legacy in {"03", "48", "9p"}:
            cr_labels.append(await t({"03": "filters.cr.03", "48": "filters.cr.48", "9p": "filters.cr.9p"}[legacy], lang))
    if cr_labels:
        field_name = await t("filters.field.cr", lang, default=("CR" if lang == "en" else "Опасность"))
        parts.append(f"{field_name}: {', '.join(cr_labels)}")

    # Types
    type_labels: List[str] = []
    selected_types = applied.get("types")
    if isinstance(selected_types, set) and selected_types:
        code_to_label = {code: label for code, label in type_options}
        for code in sorted(selected_types):
            lbl = code_to_label.get(code)
            if lbl:
                type_labels.append(str(lbl))
    if type_labels:
        field_name = await t("filters.field.type", lang, default=("Type" if lang == "en" else "Тип"))
        parts.append(f"{field_name}: {', '.join(type_labels)}")

    # Sizes
    size_labels: List[str] = []
    sizes = applied.get("sizes")
    if isinstance(sizes, set) and sizes:
        for code in ["S", "M", "L"]:
            if code in sizes:
                size_labels.append(await t(f"filters.size.{code}", lang, default=code))
    else:
        legacy_size = applied.get("size")
        if isinstance(legacy_size, str) and legacy_size in {"S", "M", "L"}:
            size_labels.append(await t(f"filters.size.{legacy_size}", lang, default=legacy_size))
    if size_labels:
        field_name = await t("filters.field.size", lang, default=("Size" if lang == "en" else "Размер"))
        parts.append(f"{field_name}: {', '.join(size_labels)}")

    # Flying
    flying = applied.get("flying")
    if flying is True or flying is False:
        field_name = await t("filters.field.flying", lang, default=("Flying" if lang == "en" else "Летающий"))
        yn = await t("filters.flying.yes", lang) if flying else await t("filters.flying.no", lang)
        parts.append(f"{field_name}: {yn}")

    # Legendary
    legendary = applied.get("legendary")
    if legendary is True or legendary is False:
        field_name = await t("filters.field.legendary", lang, default=("Legendary" if lang == "en" else "Легендарный"))
        yn = ("Yes" if lang == "en" else "Да") if legendary else ("No" if lang == "en" else "Нет")
        parts.append(f"{field_name}: {yn}")

    return "; ".join(parts) if parts else (await t("list.all.monsters", lang, default=("All monsters" if lang == "en" else "Все монстры")))


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
    rows: List[List[InlineKeyboardButton]] = []
    # Manage view: show only filters UI, no entities
    if add_menu_open:
        # Force all fields visible in manage view
        pending_for_render = {**pending, "visible_fields": ["cr_buckets", "types", "sizes", "flying"]}
        rows = await _build_filters_keyboard(pending_for_render, lang, type_options, True)
        # Add Apply button at the bottom
        rows.append([InlineKeyboardButton(await t("filters.apply", lang), callback_data="mflt:apply")])
        markup = InlineKeyboardMarkup(rows)
        # Header can still show current applied summary (doesn't list entities)
        header = await _build_filters_header(applied, lang, type_options)
        try:
            await query.edit_message_text(header, reply_markup=markup)
        except BadRequest as e:
            if "Message is not modified" in str(e):
                await query.answer()
            else:
                raise
        else:
            await query.answer()
        return

    # List view: top button Add/Change filters, then entities
    def _has_any_filters(d: Dict[str, Any]) -> bool:
        for f in ("cr_buckets", "cr_range", "types", "sizes", "size", "flying", "legendary"):
            v = d.get(f)
            if isinstance(v, set) and v:
                return True
            if v not in (None, False):
                if v is True or (isinstance(v, str) and v.strip() != ""):
                    return True
        return False

    top_label = await t("filters.change", lang) if _has_any_filters(applied) else await t("filters.add", lang)
    rows.append([InlineKeyboardButton(top_label, callback_data="mflt:add")])

    page_items = paginate(filtered, page, PAGE_SIZE_LIST)
    for m in page_items:
        label = f"{m.get('name','')}"
        rows.append([InlineKeyboardButton(label, callback_data=f"monster:detail:{m['id']}")])
    nav: List[InlineKeyboardButton] = []
    if (page - 1) * PAGE_SIZE_LIST > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"monster:list:page:{page-1}"))
    if page * PAGE_SIZE_LIST < total:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"monster:list:page:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append(await _nav_row(lang, "menu:monsters"))
    markup = InlineKeyboardMarkup(rows)
    header = await _build_filters_header(applied, lang, type_options)
    suffix = f" (p. {page})" if lang == "en" else f" (стр. {page})"
    try:
        await query.edit_message_text(header + suffix, reply_markup=markup)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            await query.answer()
        else:
            raise
    else:
        await query.answer()


async def _build_filters_keyboard(pending: Dict[str, Any], lang: str, type_options: List[Tuple[str, str]], add_menu_open: bool) -> List[List[InlineKeyboardButton]]:
    rows: List[List[InlineKeyboardButton]] = []

    # Collapsed state: only one button "Add filters"
    add_lbl = await t("filters.add", lang)
    if not add_menu_open:
        rows.append([InlineKeyboardButton(add_lbl, callback_data="mflt:add")])
        return rows

    # Manage row (expanded): only Reset (no Add here)
    reset_lbl = await t("filters.reset", lang)
    rows.append([InlineKeyboardButton(reset_lbl, callback_data="mflt:reset")])

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


