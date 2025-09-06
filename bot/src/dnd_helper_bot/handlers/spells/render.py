from typing import Any, Dict, List, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from dnd_helper_bot.repositories.api_client import api_get
from dnd_helper_bot.utils.i18n import t
from dnd_helper_bot.utils.pagination import paginate

from .filters import _filter_spells, _get_filter_state
from .lang import _resolve_lang_by_user


async def _nav_row(lang: str, back_callback: str) -> list[InlineKeyboardButton]:
    from dnd_helper_bot.utils.nav import build_nav_row

    return await build_nav_row(lang, back_callback)


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
    rows: List[List[InlineKeyboardButton]] = await _build_filters_keyboard(
        pending,
        lang,
        sorted(school_options.items(), key=lambda x: x[1].lower()),
        sorted(classes_options.items(), key=lambda x: x[1].lower()),
    )
    if total == 0:
        markup = InlineKeyboardMarkup(rows)
        await query.edit_message_text(
            await t("list.empty.spells", lang, default=("No spells." if lang == "en" else "Заклинаний нет.")),
            reply_markup=markup,
        )
        return
    page_items = paginate(filtered, page)
    for s in page_items:
        label = s.get("name", "")
        rows.append([InlineKeyboardButton(label, callback_data=f"spell:detail:{s['id']}")])
    nav: List[InlineKeyboardButton] = []
    if (page - 1) * 5 > 0:
        nav.append(
            InlineKeyboardButton(
                await t("nav.back", lang),
                callback_data=f"spell:list:page:{page-1}",
            )
        )
    if page * 5 < total:
        nav.append(
            InlineKeyboardButton(
                await t("nav.next", lang),
                callback_data=f"spell:list:page:{page+1}",
            )
        )
    if nav:
        rows.append(nav)
    rows.append(await _nav_row(lang, "menu:spells"))
    title = await t("list.title.spells", lang)
    # Keep suffix localized without i18n key, since it's numeric formatting
    suffix = f" (p. {page})" if lang == "en" else f" (стр. {page})"
    markup = InlineKeyboardMarkup(rows)
    await query.edit_message_text(title + suffix, reply_markup=markup)


async def _build_filters_keyboard(
    pending: Dict[str, Any],
    lang: str,
    school_items: List[Tuple[str, str]],
    classes_items: List[Tuple[str, str]],
) -> List[List[InlineKeyboardButton]]:
    rows: List[List[InlineKeyboardButton]] = []
    any_label = await t("filters.any", lang)
    reset_label = await t("filters.reset", lang)
    add_label = await t("filters.add", lang)

    # Manage row
    rows.append([
        InlineKeyboardButton(add_label, callback_data="sflt:add"),
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
            any_btn = InlineKeyboardButton(("✅ " if not level_selected and (pending.get("level_range") is None) else "") + any_label, callback_data="sflt:lv:any")
            row = [any_btn, InlineKeyboardButton(lv13, callback_data="sflt:lv:13"), InlineKeyboardButton(lv45, callback_data="sflt:lv:45"), InlineKeyboardButton(lv69, callback_data="sflt:lv:69")]
            row.append(InlineKeyboardButton(await t("filters.remove", lang), callback_data="sflt:rm:level_buckets"))
            rows.append(row)
        elif field == "school":
            school_selected = set(pending.get("school") or [])
            school_field_label = await t("filters.field.school", lang, default="school")
            any_school_btn = InlineKeyboardButton(("✅ " if not school_selected else "") + f"{any_label} {school_field_label}", callback_data="sflt:sc:any")
            per_row = 3
            option_buttons: List[InlineKeyboardButton] = []
            for code, label in school_items:
                text = ("✅ " if code in school_selected else "") + str(label)
                option_buttons.append(InlineKeyboardButton(text, callback_data=f"sflt:sc:{code}"))
            # First row: Any + first chunk of options
            first_chunk = option_buttons[:per_row]
            rows.append([any_school_btn] + first_chunk)
            # Subsequent rows: only options
            for i in range(per_row, len(option_buttons), per_row):
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
            rows.append([
                InlineKeyboardButton(("✅ " if state is None else "") + any_label, callback_data="sflt:conc:any"),
                InlineKeyboardButton(("✅ " if state is True else "") + await t("filters.yes", lang), callback_data="sflt:conc:yes"),
                InlineKeyboardButton(("✅ " if state is False else "") + await t("filters.no", lang), callback_data="sflt:conc:no"),
                InlineKeyboardButton(await t("filters.remove", lang), callback_data="sflt:rm:is_concentration"),
            ])
        elif field == "classes":
            classes_selected = set(pending.get("classes") or [])
            any_cls_btn = InlineKeyboardButton(("✅ " if not classes_selected else "") + any_label, callback_data="sflt:cls:any")
            per_row = 3
            current_row: List[InlineKeyboardButton] = [any_cls_btn]
            for idx, (code, label) in enumerate(classes_items):
                text = ("✅ " if code in classes_selected else "") + str(label)
                current_row.append(InlineKeyboardButton(text, callback_data=f"sflt:cls:{code}"))
                if (idx + 1) % per_row == 0:
                    rows.append(current_row)
                    current_row = [any_cls_btn]
            if current_row:
                current_row.append(InlineKeyboardButton(await t("filters.remove", lang), callback_data="sflt:rm:classes"))
                rows.append(current_row)

    return rows


