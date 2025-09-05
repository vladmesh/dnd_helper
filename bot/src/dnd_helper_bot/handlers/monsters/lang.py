async def _resolve_lang_by_user(update_or_query) -> str:
    """Prefer DB user's language; fallback to Telegram UI language."""
    try:
        # Extract telegram user id from Update or CallbackQuery
        tg_user = None
        if hasattr(update_or_query, "effective_user") and update_or_query.effective_user is not None:
            tg_user = update_or_query.effective_user
        elif hasattr(update_or_query, "from_user") and update_or_query.from_user is not None:
            tg_user = update_or_query.from_user
        tg_id = getattr(tg_user, "id", None)
        if tg_id is not None:
            from dnd_helper_bot.repositories.api_client import api_get_one

            user = await api_get_one(f"/users/by-telegram/{tg_id}")
            lang = user.get("lang")
            if lang in ("ru", "en"):
                return lang
    except Exception:
        pass
    try:
        code = None
        if hasattr(update_or_query, "effective_user") and update_or_query.effective_user is not None:
            code = (update_or_query.effective_user.language_code or "ru").lower()
        elif hasattr(update_or_query, "from_user") and update_or_query.from_user is not None:
            code = (update_or_query.from_user.language_code or "ru").lower()
        return "en" if str(code).startswith("en") else "ru"
    except Exception:
        return "ru"


