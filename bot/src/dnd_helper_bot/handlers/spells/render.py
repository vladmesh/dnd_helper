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
            }
        )

    filtered = _filter_spells(all_spells, applied)
    total = len(filtered)
    rows: List[List[InlineKeyboardButton]] = await _build_filters_keyboard(pending, lang, sorted(school_options.items(), key=lambda x: x[1].lower()))
    if total == 0:
        markup = InlineKeyboardMarkup(rows)
        await query.edit_message_text(
            await t("list.empty.spells", lang, default=("No spells." if lang == "en" else "Заклинаний нет.")),
            reply_markup=markup,
        )
        return
    page_items = paginate(filtered, page)
    for s in page_items:
        more = await t("label.more", lang)
        label = f"{more} {s.get('name','')} (#{s.get('id')})"
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


async def _build_filters_keyboard(pending: Dict[str, Any], lang: str, school_items: List[Tuple[str, str]]) -> List[List[InlineKeyboardButton]]:
    rows: List[List[InlineKeyboardButton]] = []
    # Level row: Any + buckets 13/45/69 (multi-select)
    level_selected = set(pending.get("level_buckets") or [])
    any_label = await t("filters.any", lang)
    level_field_label = await t("filters.field.level", lang, default="level")
    any_level = ("✅ " if not level_selected and (pending.get("level_range") is None) else "") + f"{any_label} {level_field_label}"
    lv13 = ("✅ " if "13" in level_selected else "") + await t("filters.level.13", lang)
    lv45 = ("✅ " if "45" in level_selected else "") + await t("filters.level.45", lang)
    lv69 = ("✅ " if "69" in level_selected else "") + await t("filters.level.69", lang)
    rows.append([
        InlineKeyboardButton(any_level, callback_data="sflt:lv:any"),
        InlineKeyboardButton(lv13, callback_data="sflt:lv:13"),
        InlineKeyboardButton(lv45, callback_data="sflt:lv:45"),
        InlineKeyboardButton(lv69, callback_data="sflt:lv:69"),
    ])

    # School row: Any + list of schools (multi-select, chunk across rows if needed)
    school_selected = set(pending.get("school") or [])
    school_field_label = await t("filters.field.school", lang, default="school")
    any_school = ("✅ " if not school_selected else "") + f"{any_label} {school_field_label}"
    current_row: List[InlineKeyboardButton] = [InlineKeyboardButton(any_school, callback_data="sflt:sc:any")]
    # put up to 3 per row after Any
    per_row = 3
    for idx, (code, label) in enumerate(school_items):
        text = ("✅ " if code in school_selected else "") + str(label)
        current_row.append(InlineKeyboardButton(text, callback_data=f"sflt:sc:{code}"))
        if (idx + 1) % per_row == 0:
            rows.append(current_row)
            current_row = [InlineKeyboardButton(any_school, callback_data="sflt:sc:any")]
    if current_row:
        rows.append(current_row)

    # Reset row only (Apply is removed in Iteration 1)
    reset = await t("filters.reset", lang)
    rows.append([InlineKeyboardButton(reset, callback_data="sflt:reset")])
    return rows


