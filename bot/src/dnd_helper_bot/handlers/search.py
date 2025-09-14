import logging
from typing import Any, Dict, List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from dnd_helper_bot.handlers.menu import (  # noqa: E402
    _build_language_keyboard,
    _build_main_menu_inline_i18n,
)
from dnd_helper_bot.handlers.monsters.lang import _resolve_lang_by_user  # type: ignore
from dnd_helper_bot.repositories.api_client import api_get, api_get_one
from dnd_helper_bot.utils.i18n import t  # noqa: E402
from dnd_helper_bot.utils.nav import build_nav_row  # noqa: E402

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

    # Cache search session data
    context.user_data["search_mode_target"] = target
    context.user_data["search_items_cache"] = items
    context.user_data["search_current_page"] = 1

    # Render paginated results (page 1)
    await _render_search_results(update, context, lang, page=1)


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


async def _build_scope_row_for_search(lang: str, context: ContextTypes.DEFAULT_TYPE) -> List[InlineKeyboardButton]:
    current = str(context.user_data.get("search_scope") or "name")
    name_label = await t("search.scope.name", lang)
    nd_label = await t("search.scope.name_description", lang)
    left = InlineKeyboardButton(("✅ " if current == "name" else "") + name_label, callback_data="scope:name")
    right = InlineKeyboardButton(("✅ " if current == "name_description" else "") + nd_label, callback_data="scope:name_description")
    return [left, right]


async def _render_search_results(update_or_query, context: ContextTypes.DEFAULT_TYPE, lang: str, page: int) -> None:
    """Render cached search results with pagination and scope row.

    Uses context.user_data keys:
      - search_mode_target: "monsters" | "spells"
      - search_items_cache: List[wrapped items]
      - search_message_id: for edit-in-place
    """
    target = context.user_data.get("search_mode_target") or "spells"
    items: List[Dict[str, Any]] = context.user_data.get("search_items_cache") or []
    total = len(items)
    context.user_data["search_current_page"] = page

    # Build rows
    rows: List[List[InlineKeyboardButton]] = []
    rows.append(await _build_scope_row_for_search(lang, context))

    # Items for the page
    from dnd_helper_bot.utils.pagination import paginate

    page_items = paginate(items, page)
    if target == "monsters":
        for m in page_items:
            try:
                e = m.get("entity") or {}
                tr = m.get("translation") or {}
                mid = e.get("id")
                if mid is None:
                    continue
                label = tr.get("name") or tr.get("description") or "<no name>"
                rows.append([InlineKeyboardButton(str(label), callback_data=f"monster:detail:{mid}")])
            except Exception:
                # Skip faulty item
                continue
    else:
        for s in page_items:
            try:
                e = s.get("entity") or {}
                tr = s.get("translation") or {}
                sid = e.get("id")
                if sid is None:
                    continue
                label = tr.get("name") or tr.get("description") or "<no name>"
                rows.append([InlineKeyboardButton(str(label), callback_data=f"spell:detail:{sid}")])
            except Exception:
                continue

    # Page navigation
    nav: List[InlineKeyboardButton] = []
    if (page - 1) * 5 > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"search:{target}:page:{page-1}"))
    if page * 5 < total:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"search:{target}:page:{page+1}"))
    if nav:
        rows.append(nav)

    # Bottom nav row (Back to section, Main)
    back_cb = "menu:monsters" if target == "monsters" else "menu:spells"
    from dnd_helper_bot.utils.nav import build_nav_row

    rows.append(await build_nav_row(lang, back_cb))

    # Title
    current = str(context.user_data.get("search_scope") or "name")
    name_label = await t("search.scope.name", lang)
    nd_label = await t("search.scope.name_description", lang)
    scope_name = name_label if current == "name" else nd_label
    title = f"[{scope_name}]\n" + await t("search.results_title", lang)
    suffix = f" (p. {page})" if lang == "en" else f" (стр. {page})"
    text = title + suffix

    # Send/edit
    active_msg_id = context.user_data.get("search_message_id")
    try:
        if hasattr(update_or_query, "callback_query") and update_or_query.callback_query:
            # From callback
            await update_or_query.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(rows))
            await update_or_query.callback_query.answer()
        else:
            # From first search via message
            msg = await update_or_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(rows))
            context.user_data["search_message_id"] = msg.message_id
            context.user_data["search_active"] = True
    except Exception:
        # Fallback: try to edit specific message if we have id
        try:
            if update_or_query.effective_chat and active_msg_id:
                await context.bot.edit_message_text(chat_id=update_or_query.effective_chat.id, message_id=active_msg_id, text=text, reply_markup=InlineKeyboardMarkup(rows))
        except Exception:
            pass


async def search_page_nav(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    try:
        _, target, _, page_s = (query.data or "").split(":", 3)
        page = int(page_s)
    except Exception:
        target = str(context.user_data.get("search_mode_target") or "spells")
        page = int(context.user_data.get("search_current_page") or 1)
    context.user_data["search_mode_target"] = target
    lang = await _resolve_lang_by_user(query)

    # Ensure items cached; if not, try to recompute from last query context if available
    items = context.user_data.get("search_items_cache")
    if not isinstance(items, list):
        # No cache: degrade gracefully to first page empty
        context.user_data["search_items_cache"] = []
    await _render_search_results(update, context, lang, page)


