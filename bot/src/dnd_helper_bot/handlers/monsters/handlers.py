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
    text = (
        f"{tdata.get('name','-')}\n"
        f"{tdata.get('description','')}\n"
        f"{await t('label.cr', lang)}: {danger_text}\n"
        f"{await t('label.hp', lang)}: {e.get('hp','-')}, {await t('label.ac', lang)}: {e.get('ac','-')}"
    )
    page = int(context.user_data.get("monsters_current_page", 1))
    markup = InlineKeyboardMarkup([await _nav_row(lang, f"monster:list:page:{page}")])
    await query.edit_message_text(text, reply_markup=markup)


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
    wrapped_list = await api_get("/monsters/wrapped-list", params={"lang": lang})
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
    text = (
        f"{tdata.get('description','')}" + await t("label.random_suffix", lang) + "\n"
        f"{await t('label.cr', lang)}: {danger_text}\n"
        f"{await t('label.hp', lang)}: {e.get('hp','-')}, {await t('label.ac', lang)}: {e.get('ac','-')}"
    )
    markup = InlineKeyboardMarkup([await _nav_row(lang, "menu:monsters")])
    await query.edit_message_text(text, reply_markup=markup)


async def monster_search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    context.user_data["awaiting_monster_query"] = True
    logger.info(
        "Monster search prompt shown",
        extra={"correlation_id": query.message.chat_id if query and query.message else None},
    )
    lang = await _resolve_lang_by_user(query)
    markup = InlineKeyboardMarkup([await _nav_row(lang, "menu:monsters")])
    await query.edit_message_text(
        await t(
            "monsters.search.prompt",
            lang,
            default="Введите подстроку для поиска по названию монстра:",
        ),
        reply_markup=markup,
    )


async def monsters_filter_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data  # e.g., mflt:leg, mflt:apply, mflt:reset
    logger.info(
        "Monsters filter action",
        extra={
            "correlation_id": query.message.chat_id if query and query.message else None,
            "action": data,
        },
    )
    pending, applied = _get_filter_state(context)
    token = data.split(":", 1)[1]
    if token == "apply":
        _set_filter_state(context, applied=dict(pending))
        page = 1
    elif token == "reset":
        _set_filter_state(
            context,
            pending=_default_monsters_filters(),
            applied=_default_monsters_filters(),
        )
        page = 1
    else:
        new_pending = _toggle_or_set_filters(pending, token)
        _set_filter_state(context, pending=new_pending)
        page = int(context.user_data.get("monsters_current_page", 1))

    await render_monsters_list(query, context, page)


