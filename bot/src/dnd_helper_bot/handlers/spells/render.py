from typing import Any, Dict, List

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
    wrapped_list: List[Dict[str, Any]] = await api_get("/spells/wrapped", params={"lang": lang})

    all_spells: List[Dict[str, Any]] = []
    for w in wrapped_list:
        e = (w.get("entity") or {})
        tdata = (w.get("translation") or {})
        all_spells.append(
            {
                "id": e.get("id"),
                "name": tdata.get("name") or "",
                "description": tdata.get("description") or "",
                "ritual": e.get("ritual"),
                "is_concentration": e.get("is_concentration"),
                "casting_time": e.get("casting_time"),
                "level": e.get("level"),
            }
        )

    filtered = _filter_spells(all_spells, applied)
    total = len(filtered)
    rows: List[List[InlineKeyboardButton]] = await _build_filters_keyboard(pending, lang)
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


async def _build_filters_keyboard(pending: Dict[str, Any], lang: str) -> List[List[InlineKeyboardButton]]:
    rit = ("✅ " if pending.get("ritual") else "") + await t("filters.ritual", lang)
    conc = ("✅ " if pending.get("is_concentration") else "") + await t("filters.concentration", lang)
    bonus = ("✅ " if pending.get("cast", {}).get("bonus") else "") + await t("filters.cast.bonus", lang)
    react = ("✅ " if pending.get("cast", {}).get("reaction") else "") + await t("filters.cast.reaction", lang)
    lv = pending.get("level_range")
    lv13 = ("✅ " if lv == "13" else "") + await t("filters.level.13", lang)
    lv45 = ("✅ " if lv == "45" else "") + await t("filters.level.45", lang)
    lv69 = ("✅ " if lv == "69" else "") + await t("filters.level.69", lang)
    apply = await t("filters.apply", lang)
    reset = await t("filters.reset", lang)
    return [
        [InlineKeyboardButton(rit, callback_data="sflt:rit"), InlineKeyboardButton(conc, callback_data="sflt:conc")],
        [InlineKeyboardButton(bonus, callback_data="sflt:ct:ba"), InlineKeyboardButton(react, callback_data="sflt:ct:re")],
        [InlineKeyboardButton(lv13, callback_data="sflt:lv:13"), InlineKeyboardButton(lv45, callback_data="sflt:lv:45"), InlineKeyboardButton(lv69, callback_data="sflt:lv:69")],
        [InlineKeyboardButton(apply, callback_data="sflt:apply"), InlineKeyboardButton(reset, callback_data="sflt:reset")],
    ]


