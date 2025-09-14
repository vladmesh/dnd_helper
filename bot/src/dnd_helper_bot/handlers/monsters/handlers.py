import html
import logging
from typing import Any, Dict

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from dnd_helper_bot.repositories.api_client import api_get, api_get_one
from dnd_helper_bot.utils.i18n import t

from .filters import (
    _default_monsters_filters,
    _get_filter_state,
    _set_filter_state,
    _toggle_or_set_filters,
)
from .lang import _resolve_lang_by_user
from .render import render_monsters_list

logger = logging.getLogger(__name__)


async def monsters_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    page = int(query.data.split(":")[-1])
    logger.info(
        "Monsters list requested",
        extra={
            "correlation_id": query.message.chat_id if query and query.message else None,
            "page": page,
        },
    )
    await render_monsters_list(query, context, page)


async def monster_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    monster_id = int(query.data.split(":")[-1])
    logger.info(
        "Monster detail requested",
        extra={
            "correlation_id": query.message.chat_id if query and query.message else None,
            "monster_id": monster_id,
        },
    )
    lang = await _resolve_lang_by_user(query)
    w = await api_get_one(f"/monsters/{monster_id}/wrapped", params={"lang": lang})
    e: Dict[str, Any] = w.get("entity") or {}
    tdata: Dict[str, Any] = w.get("translation") or {}
    labels: Dict[str, Any] = (w.get("labels") or {})
    cr_l = labels.get("cr")
    danger_text = (cr_l.get("label") if isinstance(cr_l, dict) else e.get("cr")) or "-"
    name_v = html.escape(str(tdata.get("name", "-")))
    desc_v = html.escape(str(tdata.get("description", "")))
    danger_v = html.escape(str(danger_text))
    hp_v = html.escape(str(e.get("hp", "-")))
    ac_v = html.escape(str(e.get("ac", "-")))
    text = (
        f"<b>{await t('label.name', lang)}</b>: {name_v}\n"
        f"<b>{await t('label.description', lang)}</b>: {desc_v}\n"
        f"<b>{await t('label.cr', lang)}</b>: {danger_v}\n"
        f"<b>{await t('label.hp', lang)}</b>: {hp_v}\n"
        f"<b>{await t('label.ac', lang)}</b>: {ac_v}"
    )
    page = int(context.user_data.get("monsters_current_page", 1))
    markup = InlineKeyboardMarkup([await _nav_row(lang, f"monster:list:page:{page}")])
    await query.edit_message_text(text, reply_markup=markup, parse_mode="HTML")


async def _nav_row(lang: str, back_callback: str) -> list[InlineKeyboardButton]:
    from dnd_helper_bot.utils.nav import build_nav_row

    return await build_nav_row(lang, back_callback)


async def monster_random(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    logger.info(
        "Monster random requested",
        extra={"correlation_id": query.message.chat_id if query and query.message else None},
    )
    lang = await _resolve_lang_by_user(query)
    wrapped_list = await api_get("/monsters/list/wrapped", params={"lang": lang})
    if not wrapped_list:
        logger.warning(
            "No monsters available for random",
            extra={"correlation_id": query.message.chat_id if query and query.message else None},
        )
        await query.edit_message_text(await t("list.empty.monsters", lang, default="Монстров нет."))
        return
    w = __import__("random").choice(wrapped_list)
    e: Dict[str, Any] = w.get("entity") or {}
    tdata: Dict[str, Any] = w.get("translation") or {}
    labels: Dict[str, Any] = (w.get("labels") or {})
    cr_l = labels.get("cr")
    danger_text = (cr_l.get("label") if isinstance(cr_l, dict) else e.get("cr")) or "-"
    name_v = html.escape(str(tdata.get("name", "-")))
    desc_v = html.escape(str(tdata.get("description", "")))
    danger_v = html.escape(str(danger_text))
    hp_v = html.escape(str(e.get("hp", "-")))
    ac_v = html.escape(str(e.get("ac", "-")))
    random_sfx = await t("label.random_suffix", lang)
    text = (
        f"<b>{await t('label.name', lang)}</b>: {name_v}{html.escape(random_sfx)}\n"
        f"<b>{await t('label.description', lang)}</b>: {desc_v}\n"
        f"<b>{await t('label.cr', lang)}</b>: {danger_v}\n"
        f"<b>{await t('label.hp', lang)}</b>: {hp_v}\n"
        f"<b>{await t('label.ac', lang)}</b>: {ac_v}"
    )
    markup = InlineKeyboardMarkup([await _nav_row(lang, "menu:monsters")])
    await query.edit_message_text(text, reply_markup=markup, parse_mode="HTML")


async def monster_search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    context.user_data["awaiting_monster_query"] = True
    logger.info(
        "Monster search prompt shown",
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
    nav_row = await _nav_row(lang, "menu:monsters")
    markup = InlineKeyboardMarkup([scope_row, nav_row])
    scope_name = name_label if current == "name" else nd_label
    prompt = await t(
        "monsters.search.prompt",
        lang,
        default="Введите подстроку для поиска по названию монстра:",
    )
    await query.edit_message_text(f"[{scope_name}]\n{prompt}", reply_markup=markup)


async def monsters_filter_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data  # e.g., mflt:cr:03, mflt:type:undead, mflt:reset
    logger.info(
        "Monsters filter action",
        extra={
            "correlation_id": query.message.chat_id if query and query.message else None,
            "action": data,
        },
    )
    pending, applied = _get_filter_state(context)
    token = data.split(":", 1)[1]
    if token == "reset":
        _set_filter_state(
            context,
            pending=_default_monsters_filters(),
            applied=_default_monsters_filters(),
        )
        context.user_data["monsters_add_menu_open"] = False
        page = 1
    elif token == "add":
        # toggle add submenu (enter/exit manage view)
        context.user_data["monsters_add_menu_open"] = not bool(context.user_data.get("monsters_add_menu_open"))
        page = int(context.user_data.get("monsters_current_page", 1))
    elif token == "apply":
        # apply pending to applied and exit manage view
        _set_filter_state(context, applied=pending)
        context.user_data["monsters_add_menu_open"] = False
        page = 1
    else:
        new_pending = _toggle_or_set_filters(pending, token)
        # keep manage view open while selecting; do not auto-apply
        if token.startswith("add:"):
            # still in manage view, ensure open
            context.user_data["monsters_add_menu_open"] = True
        _set_filter_state(context, pending=new_pending)
        # reset page on structure change, but stay on current page otherwise
        page = 1 if token.endswith(":any") or token.startswith("add:") or token.startswith("rm:") else int(context.user_data.get("monsters_current_page", 1))

    await render_monsters_list(query, context, page)


