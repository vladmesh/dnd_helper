import logging
import html
from typing import Any, Dict

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from dnd_helper_bot.repositories.api_client import api_get, api_get_one
from dnd_helper_bot.utils.i18n import t

from .filters import (
    _default_spells_filters,
    _get_filter_state,
    _set_filter_state,
    _toggle_or_set_filters,
)
from .lang import _resolve_lang_by_user
from .render import render_spells_list

logger = logging.getLogger(__name__)


async def spells_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    page = int(query.data.split(":")[-1])
    logger.info(
        "Spells list requested",
        extra={
            "correlation_id": query.message.chat_id if query and query.message else None,
            "page": page,
        },
    )
    await render_spells_list(query, context, page)


async def spell_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    spell_id = int(query.data.split(":")[-1])
    logger.info(
        "Spell detail requested",
        extra={
            "correlation_id": query.message.chat_id if query and query.message else None,
            "spell_id": spell_id,
        },
    )
    lang = await _resolve_lang_by_user(query)
    w = await api_get_one(f"/spells/{spell_id}/wrapped", params={"lang": lang})
    e: Dict[str, Any] = w.get("entity") or {}
    tdata: Dict[str, Any] = w.get("translation") or {}
    labels: Dict[str, Any] = w.get("labels") or {}
    classes_l = labels.get("classes") or []
    classes_str = ", ".join([(c.get("label") or c.get("code")) for c in classes_l]) if classes_l else "-"
    school_l = labels.get("school") or {}
    school_str = school_l.get("label") if isinstance(school_l, dict) else (e.get("school") or "-")
    name_v = html.escape(str(tdata.get("name", "-")))
    desc_v = html.escape(str(tdata.get("description", "")))
    level_v = html.escape(str(e.get("level", "-")))
    classes_v = html.escape(str(classes_str))
    school_v = html.escape(str(school_str))
    text = (
        f"<b>{await t('label.name', lang)}</b>: {name_v}\n"
        f"<b>{await t('label.description', lang)}</b>: {desc_v}\n"
        f"<b>{await t('spells.detail.level', lang)}</b>: {level_v}\n"
        f"<b>{await t('spells.detail.classes', lang)}</b>: {classes_v}\n"
        f"<b>{await t('spells.detail.school', lang)}</b>: {school_v}"
    )
    page = int(context.user_data.get("spells_current_page", 1))
    markup = InlineKeyboardMarkup([await _nav_row(lang, f"spell:list:page:{page}")])
    await query.edit_message_text(text, reply_markup=markup, parse_mode="HTML")


async def _nav_row(lang: str, back_callback: str) -> list[InlineKeyboardButton]:
    from dnd_helper_bot.utils.nav import build_nav_row

    return await build_nav_row(lang, back_callback)


async def spell_random(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    logger.info(
        "Spell random requested",
        extra={"correlation_id": query.message.chat_id if query and query.message else None},
    )
    lang = await _resolve_lang_by_user(query)
    wrapped_list = await api_get("/spells/list/wrapped", params={"lang": lang})
    if not wrapped_list:
        logger.warning(
            "No spells available for random",
            extra={"correlation_id": query.message.chat_id if query and query.message else None},
        )
        await query.edit_message_text(await t("list.empty.spells", lang, default="Заклинаний нет."))
        return
    w = __import__("random").choice(wrapped_list)
    e: Dict[str, Any] = w.get("entity") or {}
    tdata: Dict[str, Any] = w.get("translation") or {}
    labels: Dict[str, Any] = w.get("labels") or {}
    classes_l = labels.get("classes") or []
    classes_str = ", ".join([(c.get("label") or c.get("code")) for c in classes_l]) if classes_l else "-"
    school_l = labels.get("school") or {}
    school_str = school_l.get("label") if isinstance(school_l, dict) else (e.get("school") or "-")
    name_v = html.escape(str(tdata.get("name", "-")))
    desc_v = html.escape(str(tdata.get("description", "")))
    level_v = html.escape(str(e.get("level", "-")))
    classes_v = html.escape(str(classes_str))
    school_v = html.escape(str(school_str))
    random_sfx = await t("label.random_suffix", lang)
    text = (
        f"<b>{await t('label.name', lang)}</b>: {name_v}{html.escape(random_sfx)}\n"
        f"<b>{await t('label.description', lang)}</b>: {desc_v}\n"
        f"<b>{await t('spells.detail.level', lang)}</b>: {level_v}\n"
        f"<b>{await t('spells.detail.classes', lang)}</b>: {classes_v}\n"
        f"<b>{await t('spells.detail.school', lang)}</b>: {school_v}"
    )
    markup = InlineKeyboardMarkup([await _nav_row(lang, "menu:spells")])
    await query.edit_message_text(text, reply_markup=markup, parse_mode="HTML")


async def spell_search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    context.user_data["awaiting_spell_query"] = True
    logger.info(
        "Spell search prompt shown",
        extra={"correlation_id": query.message.chat_id if query and query.message else None},
    )
    lang = await _resolve_lang_by_user(query)
    # Ensure default scope is set
    if not context.user_data.get("search_scope"):
        context.user_data["search_scope"] = "name"
    # Build scope row inline
    from dnd_helper_bot.utils.i18n import t as _t
    current = str(context.user_data.get("search_scope") or "name")
    name_label = await _t("search.scope.name", lang)
    nd_label = await _t("search.scope.name_description", lang)
    scope_row = [
        InlineKeyboardButton(("✅ " if current == "name" else "") + name_label, callback_data="scope:name"),
        InlineKeyboardButton(("✅ " if current == "name_description" else "") + nd_label, callback_data="scope:name_description"),
    ]
    nav_row = await _nav_row(lang, "menu:spells")
    markup = InlineKeyboardMarkup([scope_row, nav_row])
    scope_name = name_label if current == "name" else nd_label
    prompt = await t(
        "spells.search.prompt",
        lang,
        default="Введите подстроку для поиска по названию заклинания:",
    )
    await query.edit_message_text(f"[{scope_name}]\n{prompt}", reply_markup=markup)


async def spells_filter_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data  # e.g., sflt:rit, sflt:lv:13, sflt:sc:any, sflt:reset
    pending, applied = _get_filter_state(context)
    logger.info(
        "Spells filter action",
        extra={
            "correlation_id": query.message.chat_id if query and query.message else None,
            "action": data,
            "visible_fields": list(pending.get("visible_fields") or []),
        },
    )
    token = data.split(":", 1)[1]
    if token == "reset":
        _set_filter_state(
            context,
            pending=_default_spells_filters(),
            applied=_default_spells_filters(),
        )
        page = 1
    else:
        new_pending = _toggle_or_set_filters(pending, token)
        # Immediate apply
        _set_filter_state(context, pending=new_pending, applied={**new_pending, "cast": {**new_pending.get("cast", {})}})
        # Reset to first page on structural changes (Any <-> some, add/remove field, add menu open/close)
        if token.startswith(("lv:", "sc:", "ct:", "cls:", "rit:", "conc:")) or token.startswith(("add", "rm:")):
            page = 1
        else:
            page = int(context.user_data.get("spells_current_page", 1))

    await render_spells_list(query, context, page)


