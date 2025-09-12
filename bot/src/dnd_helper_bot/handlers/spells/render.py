from typing import Any, Dict, List, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from dnd_helper_bot.repositories.api_client import api_get
from dnd_helper_bot.utils.i18n import t
from dnd_helper_bot.utils.pagination import paginate, PAGE_SIZE_LIST

from .filters import _filter_spells, _get_filter_state
from .lang import _resolve_lang_by_user


async def _nav_row(lang: str, back_callback: str) -> list[InlineKeyboardButton]:
    from dnd_helper_bot.utils.nav import build_nav_row

    return await build_nav_row(lang, back_callback)


async def _build_filters_header(applied: Dict[str, Any], lang: str, school_items: List[Tuple[str, str]]) -> str:
    # Nothing applied → "All spells"
    has_any = False
    for f in ("level_buckets", "level_range", "school", "casting_time", "classes", "ritual", "is_concentration"):
        v = applied.get(f)
        if isinstance(v, set) and v:
            has_any = True
            break
        if v not in (None, False):
            if v is True or (isinstance(v, str) and v.strip() != ""):
                has_any = True
                break
    if not has_any:
        default_text = "All spells" if lang == "en" else "Все заклинания"
        return await t("list.all.spells", lang, default=default_text)

    parts: List[str] = []
    # Level buckets
    level_labels: List[str] = []
    lb = applied.get("level_buckets")
    if isinstance(lb, set) and lb:
        code_to_key = {"13": "filters.level.13", "45": "filters.level.45", "69": "filters.level.69"}
        for code in ("13", "45", "69"):
            if code in lb:
                level_labels.append(await t(code_to_key[code], lang))
    else:
        legacy = applied.get("level_range")
        if isinstance(legacy, str) and legacy in {"13", "45", "69"}:
            level_labels.append(await t({"13": "filters.level.13", "45": "filters.level.45", "69": "filters.level.69"}[legacy], lang))
    if level_labels:
        field_name = await t("filters.field.level", lang, default=("Level" if lang == "en" else "Уровень"))
        parts.append(f"{field_name}: {', '.join(level_labels)}")

    # School
    school_labels: List[str] = []
    selected_school = applied.get("school")
    if isinstance(selected_school, set) and selected_school:
        code_to_label = {code: label for code, label in school_items}
        for code in sorted(selected_school):
            lbl = code_to_label.get(code)
            if lbl:
                school_labels.append(str(lbl))
    if school_labels:
        field_name = await t("filters.field.school", lang, default=("School" if lang == "en" else "Школа"))
        parts.append(f"{field_name}: {', '.join(school_labels)}")

    # Casting time
    ct = applied.get("casting_time")
    if isinstance(ct, set) and ct:
        items: List[str] = []
        if "ba" in ct:
            items.append(await t("filters.cast.bonus", lang))
        if "re" in ct:
            items.append(await t("filters.cast.reaction", lang))
        if items:
            field_name = await t("filters.field.casting_time", lang, default=("Casting" if lang == "en" else "Время"))
            parts.append(f"{field_name}: {', '.join(items)}")

    # Ritual
    if applied.get("ritual") is True or applied.get("ritual") is False:
        yn = await t("filters.yes", lang) if applied.get("ritual") else await t("filters.no", lang)
        field_name = await t("filters.ritual", lang, default=("Ritual" if lang == "en" else "Ритуал"))
        parts.append(f"{field_name}: {yn}")

    # Concentration
    if applied.get("is_concentration") is True or applied.get("is_concentration") is False:
        yn = await t("filters.yes", lang) if applied.get("is_concentration") else await t("filters.no", lang)
        field_name = await t("filters.field.concentration", lang, default=("Concentration" if lang == "en" else "Концентрация"))
        parts.append(f"{field_name}: {yn}")

    # Classes
    classes = applied.get("classes")
    if isinstance(classes, set) and classes:
        field_name = await t("filters.field.class", lang, default=("Class" if lang == "en" else "Класс"))
        parts.append(f"{field_name}: {', '.join(sorted(classes))}")

    return "; ".join(parts) if parts else (await t("list.all.spells", lang, default=("All spells" if lang == "en" else "Все заклинания")))
async def render_spells_list(query, context: ContextTypes.DEFAULT_TYPE, page: int) -> None:
    context.user_data["spells_current_page"] = page
    pending, applied = _get_filter_state(context)
    lang = await _resolve_lang_by_user(query)
    wrapped_list: List[Dict[str, Any]] = await api_get("/spells/list/wrapped", params={"lang": lang})

    all_spells: List[Dict[str, Any]] = []
    school_options: Dict[str, str] = {}
    classes_options: Dict[str, str] = {}
    for w in wrapped_list:
        e = (w.get("entity") or {})
        tdata = (w.get("translation") or {})
        labels = (w.get("labels") or {})
        # collect school label mapping if available
        school_label_obj = labels.get("school") or {}
        school_code = school_label_obj.get("code") if isinstance(school_label_obj, dict) else (e.get("school"))
        school_label = school_label_obj.get("label") if isinstance(school_label_obj, dict) else (school_code or "")
        if school_code:
            school_options[str(school_code)] = str(school_label or school_code)
        # collect classes labels/codes
        for c in (labels.get("classes") or []):
            code = str(c.get("code"))
            label = str(c.get("label") or code)
            if code:
                classes_options[code] = label
        all_spells.append(
            {
                "id": e.get("id"),
                "name": tdata.get("name") or "",
                "description": tdata.get("description") or "",
                "ritual": e.get("ritual"),
                "is_concentration": e.get("is_concentration"),
                "casting_time": e.get("casting_time"),
                "level": e.get("level"),
                "school": e.get("school"),
                "classes": [str(c.get("code")) for c in (labels.get("classes") or []) if c.get("code") is not None],
            }
        )

    filtered = _filter_spells(all_spells, applied)
    total = len(filtered)
    try:
        import logging
        logging.getLogger(__name__).info(
            "Spells filtered",
            extra={
                "total": total,
                "page": page,
                "visible_fields": list(pending.get("visible_fields") or []),
                "selected": {
                    "level_buckets": list(pending.get("level_buckets") or []),
                    "school": list(pending.get("school") or []),
                    "casting_time": list(pending.get("casting_time") or []),
                    "classes": list(pending.get("classes") or []),
                    "ritual": pending.get("ritual"),
                    "is_concentration": pending.get("is_concentration"),
                },
            },
        )
    except Exception:
        pass
    rows: List[List[InlineKeyboardButton]] = []
    school_items_sorted = sorted(school_options.items(), key=lambda x: x[1].lower())
    classes_items_sorted = sorted(classes_options.items(), key=lambda x: x[1].lower())
    # Manage view: only filters UI, no entities
    add_menu_open = bool(context.user_data.get("spells_add_menu_open"))
    if add_menu_open:
        # Show all available filter rows in manage view
        pending_for_render = {
            **pending,
            "visible_fields": [
                "level_buckets",
                "school",
                "casting_time",
                "ritual",
                "is_concentration",
                "classes",
            ],
            "add_menu_open": True,
        }
        rows = await _build_filters_keyboard(pending_for_render, lang, school_items_sorted, classes_items_sorted)
        rows.append([InlineKeyboardButton(await t("filters.apply", lang), callback_data="sflt:apply")])
        markup = InlineKeyboardMarkup(rows)
        header = await _build_filters_header(applied, lang, school_items_sorted)
        await query.edit_message_text(header, reply_markup=markup)
        return

    # List view: top button Add/Change filters, then entities
    def _has_any_filters(d: Dict[str, Any]) -> bool:
        for f in ("level_buckets", "level_range", "school", "casting_time", "classes", "ritual", "is_concentration"):
            v = d.get(f)
            if isinstance(v, set) and v:
                return True
            if v not in (None, False):
                if v is True or (isinstance(v, str) and v.strip() != ""):
                    return True
        return False

    top_label = await t("filters.change", lang) if _has_any_filters(applied) else await t("filters.add", lang)
    rows.append([InlineKeyboardButton(top_label, callback_data="sflt:add")])

    if total == 0:
        markup = InlineKeyboardMarkup(rows)
        await query.edit_message_text(
            await t("list.empty.spells", lang, default=("No spells." if lang == "en" else "Заклинаний нет.")),
            reply_markup=markup,
        )
        return
    page_items = paginate(filtered, page, PAGE_SIZE_LIST)
    for s in page_items:
        label = s.get("name", "")
        rows.append([InlineKeyboardButton(label, callback_data=f"spell:detail:{s['id']}")])
    nav: List[InlineKeyboardButton] = []
    if (page - 1) * PAGE_SIZE_LIST > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"spell:list:page:{page-1}"))
    if page * PAGE_SIZE_LIST < total:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"spell:list:page:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append(await _nav_row(lang, "menu:spells"))
    # Keep suffix localized without i18n key, since it's numeric formatting
    suffix = f" (p. {page})" if lang == "en" else f" (стр. {page})"
    markup = InlineKeyboardMarkup(rows)
    header = await _build_filters_header(applied, lang, school_items_sorted)
    await query.edit_message_text(header + suffix, reply_markup=markup)


async def _build_filters_keyboard(
    pending: Dict[str, Any],
    lang: str,
    school_items: List[Tuple[str, str]],
    classes_items: List[Tuple[str, str]],
) -> List[List[InlineKeyboardButton]]:
    rows: List[List[InlineKeyboardButton]] = []
    any_label = await t("filters.any", lang)
    add_label = await t("filters.add", lang)

    # Collapsed state: only one button "Add filters"
    if not bool(pending.get("add_menu_open")):
        rows.append([InlineKeyboardButton(add_label, callback_data="sflt:add")])
        return rows

    reset_label = await t("filters.reset", lang)
    # Manage row (expanded): only Reset (no Add here)
    rows.append([
        InlineKeyboardButton(reset_label, callback_data="sflt:reset"),
    ])

    # Add submenu
    if pending.get("add_menu_open"):
        candidates = ["casting_time", "ritual", "is_concentration", "classes"]
        visible = set(pending.get("visible_fields") or [])
        submenu: List[InlineKeyboardButton] = []
        for field in candidates:
            if field in visible:
                continue
            if field == "casting_time":
                # Compose label from existing keys
                ct_label = f"{await t('filters.cast.bonus', lang)} / {await t('filters.cast.reaction', lang)}"
                submenu.append(InlineKeyboardButton(ct_label, callback_data="sflt:add:casting_time"))
            elif field == "ritual":
                submenu.append(InlineKeyboardButton(await t("filters.ritual", lang), callback_data="sflt:add:ritual"))
            elif field == "is_concentration":
                submenu.append(InlineKeyboardButton(await t("filters.concentration", lang), callback_data="sflt:add:is_concentration"))
            elif field == "classes":
                submenu.append(InlineKeyboardButton(await t("spells.detail.classes", lang), callback_data="sflt:add:classes"))
        if submenu:
            rows.append(submenu)

    # Render rows per visible_fields
    visible_fields: List[str] = list(pending.get("visible_fields") or ["level_buckets", "school"])
    for field in visible_fields:
        if field == "level_buckets":
            level_selected = set(pending.get("level_buckets") or [])
            lv13 = ("✅ " if "13" in level_selected else "") + await t("filters.level.13", lang)
            lv45 = ("✅ " if "45" in level_selected else "") + await t("filters.level.45", lang)
            lv69 = ("✅ " if "69" in level_selected else "") + await t("filters.level.69", lang)
            any_level_text = await t("filters.any.level", lang, default=f"{any_label} " + (await t("filters.field.level", lang, default="level")))
            # Row with Any only
            rows.append([InlineKeyboardButton(("✅ " if not level_selected and (pending.get("level_range") is None) else "") + any_level_text, callback_data="sflt:lv:any")])
            # Row with buckets
            rows.append([
                InlineKeyboardButton(lv13, callback_data="sflt:lv:13"),
                InlineKeyboardButton(lv45, callback_data="sflt:lv:45"),
                InlineKeyboardButton(lv69, callback_data="sflt:lv:69"),
                InlineKeyboardButton(await t("filters.remove", lang), callback_data="sflt:rm:level_buckets"),
            ])
        elif field == "school":
            school_selected = set(pending.get("school") or [])
            any_school_text = await t("filters.any.school", lang, default=f"{any_label} " + (await t("filters.field.school", lang, default="school")))
            any_school_btn = InlineKeyboardButton(("✅ " if not school_selected else "") + any_school_text, callback_data="sflt:sc:any")
            per_row = 3
            option_buttons: List[InlineKeyboardButton] = []
            for code, label in school_items:
                text = ("✅ " if code in school_selected else "") + str(label)
                option_buttons.append(InlineKeyboardButton(text, callback_data=f"sflt:sc:{code}"))
            # First row: Any only
            rows.append([any_school_btn])
            # Subsequent rows: only options
            for i in range(0, len(option_buttons), per_row):
                rows.append(option_buttons[i : i + per_row])
            # Append Hide to the last school row
            if rows:
                rows[-1].append(InlineKeyboardButton(await t("filters.remove", lang), callback_data="sflt:rm:school"))
        elif field == "casting_time":
            ct_selected = set(pending.get("casting_time") or [])
            any_ct = InlineKeyboardButton(("✅ " if not ct_selected else "") + any_label, callback_data="sflt:ct:any")
            bonus = ("✅ " if "ba" in ct_selected else "") + await t("filters.cast.bonus", lang)
            react = ("✅ " if "re" in ct_selected else "") + await t("filters.cast.reaction", lang)
            rows.append([any_ct, InlineKeyboardButton(bonus, callback_data="sflt:ct:ba"), InlineKeyboardButton(react, callback_data="sflt:ct:re"), InlineKeyboardButton(await t("filters.remove", lang), callback_data="sflt:rm:casting_time")])
        elif field == "ritual":
            state = pending.get("ritual")
            rows.append([
                InlineKeyboardButton(("✅ " if state is None else "") + any_label, callback_data="sflt:rit:any"),
                InlineKeyboardButton(("✅ " if state is True else "") + await t("filters.yes", lang), callback_data="sflt:rit:yes"),
                InlineKeyboardButton(("✅ " if state is False else "") + await t("filters.no", lang), callback_data="sflt:rit:no"),
                InlineKeyboardButton(await t("filters.remove", lang), callback_data="sflt:rm:ritual"),
            ])
        elif field == "is_concentration":
            state = pending.get("is_concentration")
            any_conc_text = await t("filters.any.concentration", lang, default=(any_label + " " + (await t("filters.field.concentration", lang, default="concentration"))))
            rows.append([
                InlineKeyboardButton(("✅ " if state is None else "") + any_conc_text, callback_data="sflt:conc:any"),
                InlineKeyboardButton(("✅ " if state is True else "") + await t("filters.yes", lang), callback_data="sflt:conc:yes"),
                InlineKeyboardButton(("✅ " if state is False else "") + await t("filters.no", lang), callback_data="sflt:conc:no"),
                InlineKeyboardButton(await t("filters.remove", lang), callback_data="sflt:rm:is_concentration"),
            ])
        elif field == "classes":
            classes_selected = set(pending.get("classes") or [])
            any_cls_text = await t("filters.any.class", lang, default=(any_label + " " + (await t("filters.field.class", lang, default="class"))))
            any_cls_btn = InlineKeyboardButton(("✅ " if not classes_selected else "") + any_cls_text, callback_data="sflt:cls:any")
            per_row = 3
            option_buttons: List[InlineKeyboardButton] = []
            for code, label in classes_items:
                text = ("✅ " if code in classes_selected else "") + str(label)
                option_buttons.append(InlineKeyboardButton(text, callback_data=f"sflt:cls:{code}"))
            # First row: Any only
            rows.append([any_cls_btn])
            # Subsequent rows: only options
            for i in range(0, len(option_buttons), per_row):
                rows.append(option_buttons[i : i + per_row])
            # Append Hide to the last classes row
            if rows:
                rows[-1].append(InlineKeyboardButton(await t("filters.remove", lang), callback_data="sflt:rm:classes"))

    return rows


