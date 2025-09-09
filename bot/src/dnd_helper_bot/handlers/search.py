import logging
from typing import Any, Dict, List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from dnd_helper_bot.handlers.menu import (  # noqa: E402
    _build_language_keyboard,
    _build_main_menu_inline_i18n,
)
from dnd_helper_bot.repositories.api_client import api_get, api_get_one
from dnd_helper_bot.utils.i18n import t  # noqa: E402
from dnd_helper_bot.utils.nav import build_nav_row  # noqa: E402
from dnd_helper_bot.handlers.monsters.lang import _resolve_lang_by_user  # type: ignore

logger = logging.getLogger(__name__)


async def handle_search_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Dice flow takes precedence if active
    if context.user_data.get("awaiting_dice_count") or context.user_data.get("awaiting_dice_faces"):
        from dnd_helper_bot.handlers.dice import (
            handle_dice_text_input,  # local import to avoid cycle
        )
        await handle_dice_text_input(update, context)
        return

    # Ensure user exists; if not, ask for language first
    try:
        tg_id = update.effective_user.id if update.effective_user else None
        user = await api_get_one(f"/users/by-telegram/{tg_id}")
        lang = user.get("lang", "ru")
    except Exception:
        logger.exception("Failed to fetch user by telegram id")
        # Not registered: show only language selection keyboard (no back)
        # Determine UI language from Telegram
        try:
            code = (update.effective_user.language_code or "ru").lower()
            lang_guess = "en" if str(code).startswith("en") else "ru"
        except Exception:
            lang_guess = "ru"
        await update.message.reply_text(
            await t("settings.choose_language_prompt", lang_guess),
            reply_markup=await _build_language_keyboard(include_back=False, lang=lang_guess),
        )
        return

    awaiting_monster = bool(context.user_data.get("awaiting_monster_query"))
    awaiting_spell = bool(context.user_data.get("awaiting_spell_query"))
    # Allow continuing search from results page (edit in place)
    active_target = context.user_data.get("search_mode_target")
    active_msg_id = context.user_data.get("search_message_id")
    search_active = bool(context.user_data.get("search_active"))
    continuing = (not awaiting_monster and not awaiting_spell) and (
        search_active or (active_target in {"monsters", "spells"} and bool(active_msg_id))
    )
    logger.info(
        "Search state",
        extra={
            "awaiting_monster": awaiting_monster,
            "awaiting_spell": awaiting_spell,
            "continuing": continuing,
            "active_target": active_target,
            "active_msg_id": active_msg_id,
            "search_active": search_active,
        },
    )
    if not (awaiting_monster or awaiting_spell or continuing):
        logger.info(
            "Search fallback to main menu",
            extra={
                "awaiting_monster": awaiting_monster,
                "awaiting_spell": awaiting_spell,
                "continuing": continuing,
                "active_target": active_target,
                "active_msg_id": active_msg_id,
                "search_active": search_active,
            },
        )
        # Not in search mode: show inline main menu directly
        await update.message.reply_text(
            await t("search.select_action", lang),
            reply_markup=await _build_main_menu_inline_i18n(lang),
        )
        return

    if awaiting_monster:
        context.user_data.pop("awaiting_monster_query", None)
    if awaiting_spell:
        context.user_data.pop("awaiting_spell_query", None)

    query_text = (update.message.text or "").strip()
    if not query_text:
        logger.warning("Empty search query", extra={"correlation_id": update.effective_chat.id if update.effective_chat else None})
        await update.message.reply_text(
            await t("search.empty_query", lang),
            reply_markup=await _build_main_menu_inline_i18n(lang),
        )
        return

    try:
        scope = str(context.user_data.get("search_scope") or "name")
        params = {"q": query_text, "lang": lang, "search_scope": scope}
        logger.info(
            "Search request",
            extra={
                "correlation_id": update.effective_chat.id if update.effective_chat else None,
                "q": query_text,
                "lang": lang,
                "target": "monsters" if awaiting_monster else "spells",
            },
        )
        target = (
            "monsters" if awaiting_monster or (continuing and active_target == "monsters") else "spells"
        )
        if target == "monsters":
            items: List[Dict[str, Any]] = await api_get("/monsters/search/wrapped", params=params)
        else:
            items = await api_get("/spells/search/wrapped", params=params)
        logger.info(
            "Search response",
            extra={
                "correlation_id": update.effective_chat.id if update.effective_chat else None,
                "count": len(items) if isinstance(items, list) else None,
                "sample_keys": (list(items[0].keys()) if isinstance(items, list) and items else []),
            },
        )
    except Exception:
        logger.exception("API search request failed")
        await update.message.reply_text(await t("search.api_error", lang))
        return

    if not items:
        logger.info("Search no results", extra={"correlation_id": update.effective_chat.id if update.effective_chat else None, "query": query_text})
        # Build scope row (always visible) and nav row
        current_scope = str(context.user_data.get("search_scope") or "name")
        name_label_ = await t("search.scope.name", lang)
        nd_label_ = await t("search.scope.name_description", lang)
        scope_row_ = [
            InlineKeyboardButton(("✅ " if current_scope == "name" else "") + name_label_, callback_data="scope:name"),
            InlineKeyboardButton(("✅ " if current_scope == "name_description" else "") + nd_label_, callback_data="scope:name_description"),
        ]
        back_cb = "menu:monsters" if (awaiting_monster or (continuing and active_target == "monsters")) else "menu:spells"
        nav = await build_nav_row(lang, back_cb)
        markup = InlineKeyboardMarkup([scope_row_, nav])
        title = await t("search.no_results", lang)
        # Edit in place if continuing, else send new message and start active session
        if continuing and active_msg_id and update.effective_chat:
            try:
                await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=active_msg_id, text=title, reply_markup=markup)
                return
            except Exception:
                pass
        msg = await update.message.reply_text(title, reply_markup=markup)
        # Start/refresh active search session context
        context.user_data["search_mode_target"] = (
            "monsters" if awaiting_monster or (continuing and active_target == "monsters") else "spells"
        )
        context.user_data["search_message_id"] = msg.message_id
        context.user_data["search_active"] = True
        return

    rows: List[List[InlineKeyboardButton]] = []
    # Always show current search scope toggle row at the top of results
    async def _build_scope_row(lang: str) -> List[InlineKeyboardButton]:
        current = str(context.user_data.get("search_scope") or "name")
        name_label = await t("search.scope.name", lang)
        nd_label = await t("search.scope.name_description", lang)
        left = InlineKeyboardButton(("✅ " if current == "name" else "") + name_label, callback_data="scope:name")
        right = InlineKeyboardButton(("✅ " if current == "name_description" else "") + nd_label, callback_data="scope:name_description")
        return [left, right]
    if awaiting_monster:
        for m in items[:10]:
            try:
                e = m.get("entity") or {}
                tr = m.get("translation") or {}
                mid = e.get("id")
                if mid is None:
                    logger.warning("Search item missing entity.id", extra={"item_keys": list(m.keys())})
                    continue
                label = tr.get("name") or tr.get("description") or "<no name>"
                if not tr.get("name"):
                    logger.info("Search item label from description", extra={"id": mid})
                rows.append([InlineKeyboardButton(str(label), callback_data=f"monster:detail:{mid}")])
            except Exception:
                logger.exception("Failed to render monster search item")
    else:
        for s in items[:10]:
            try:
                e = s.get("entity") or {}
                tr = s.get("translation") or {}
                sid = e.get("id")
                if sid is None:
                    logger.warning("Search item missing entity.id", extra={"item_keys": list(s.keys())})
                    continue
                label = tr.get("name") or tr.get("description") or "<no name>"
                if not tr.get("name"):
                    logger.info("Search item label from description", extra={"id": sid})
                rows.append([InlineKeyboardButton(str(label), callback_data=f"spell:detail:{sid}")])
            except Exception:
                logger.exception("Failed to render spell search item")

    # Prepend scope row
    rows.insert(0, await _build_scope_row(lang))
    rows.append([InlineKeyboardButton(await t("nav.main", lang), callback_data="menu:main")])
    logger.info("Search results shown", extra={"correlation_id": update.effective_chat.id if update.effective_chat else None, "count": len(rows) - 1})

    # Title with active scope label
    current = str(context.user_data.get("search_scope") or "name")
    name_label = await t("search.scope.name", lang)
    nd_label = await t("search.scope.name_description", lang)
    scope_name = name_label if current == "name" else nd_label
    markup = InlineKeyboardMarkup(rows)
    text = f"[{scope_name}]\n" + await t("search.results_title", lang)
    if continuing and active_msg_id and update.effective_chat:
        try:
            await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=active_msg_id, text=text, reply_markup=markup)
            return
        except Exception:
            pass
    # First search: send new message and remember to enable edit-in-place for subsequent queries
    msg = await update.message.reply_text(text, reply_markup=markup)
    context.user_data["search_mode_target"] = target
    context.user_data["search_message_id"] = msg.message_id
    context.user_data["search_active"] = True


async def toggle_search_scope(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    try:
        _, value = (query.data or "").split(":", 1)
    except Exception:
        value = "name"
    if value not in {"name", "name_description"}:
        value = "name"
    context.user_data["search_scope"] = value
    lang = await _resolve_lang_by_user(query)

    # Rebuild only the scope row and update current message markup, preserving other rows
    name_label = await t("search.scope.name", lang)
    nd_label = await t("search.scope.name_description", lang)
    left = InlineKeyboardButton(("✅ " if value == "name" else "") + name_label, callback_data="scope:name")
    right = InlineKeyboardButton(("✅ " if value == "name_description" else "") + nd_label, callback_data="scope:name_description")
    scope_row = [left, right]

    existing = query.message.reply_markup.inline_keyboard if query.message and query.message.reply_markup else []
    # Normalize to list[list[InlineKeyboardButton]]
    existing_rows: List[List[InlineKeyboardButton]] = [list(row) for row in (existing or [])]
    if existing_rows:
        new_keyboard: List[List[InlineKeyboardButton]] = [scope_row] + existing_rows[1:]
    else:
        new_keyboard = [scope_row]
    try:
        await query.edit_message_reply_markup(InlineKeyboardMarkup(new_keyboard))
    except Exception:
        # If edit fails (stale), ignore; scope is saved for next interactions
        pass


