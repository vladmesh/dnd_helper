import logging
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
    text = (
        f"{tdata.get('name','-')}\n"
        f"{tdata.get('description','')}\n"
        f"{await t('spells.detail.classes', lang)}: {classes_str}\n"
        f"{await t('spells.detail.school', lang)}: {school_str}"
    )
    page = int(context.user_data.get("spells_current_page", 1))
    markup = InlineKeyboardMarkup([await _nav_row(lang, f"spell:list:page:{page}")])
    await query.edit_message_text(text, reply_markup=markup)


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
    wrapped_list = await api_get("/spells/wrapped", params={"lang": lang})
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
    text = (
        f"{tdata.get('description','')}"
        + await t("label.random_suffix", lang)
        + "\n"
        + f"{await t('spells.detail.classes', lang)}: {classes_str}\n"
        + f"{await t('spells.detail.school', lang)}: {school_str}"
    )
    markup = InlineKeyboardMarkup([await _nav_row(lang, "menu:spells")])
    await query.edit_message_text(text, reply_markup=markup)


async def spell_search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    context.user_data["awaiting_spell_query"] = True
    logger.info(
        "Spell search prompt shown",
        extra={"correlation_id": query.message.chat_id if query and query.message else None},
    )
    lang = await _resolve_lang_by_user(query)
    markup = InlineKeyboardMarkup([await _nav_row(lang, "menu:spells")])
    await query.edit_message_text(
        await t(
            "spells.search.prompt",
            lang,
            default="Введите подстроку для поиска по названию заклинания:",
        ),
        reply_markup=markup,
    )


async def spells_filter_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data  # e.g., sflt:rit, sflt:apply, sflt:reset
    logger.info(
        "Spells filter action",
        extra={
            "correlation_id": query.message.chat_id if query and query.message else None,
            "action": data,
        },
    )
    pending, applied = _get_filter_state(context)
    token = data.split(":", 1)[1]
    if token == "apply":
        _set_filter_state(context, applied={**pending, "cast": {**pending.get("cast", {})}})
        page = 1
    elif token == "reset":
        _set_filter_state(
            context,
            pending=_default_spells_filters(),
            applied=_default_spells_filters(),
        )
        page = 1
    else:
        new_pending = _toggle_or_set_filters(pending, token)
        _set_filter_state(context, pending=new_pending)
        page = int(context.user_data.get("spells_current_page", 1))

    await render_spells_list(query, context, page)


