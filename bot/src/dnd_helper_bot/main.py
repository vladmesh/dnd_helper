import asyncio
import os
import logging

from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from dnd_helper_bot.handlers.dice import dice_roll, show_dice_menu_from_callback
from dnd_helper_bot.handlers.menu import (
    show_bestiarie_menu_from_callback,
    show_main_menu_from_callback,
    show_spells_menu_from_callback,
    show_settings_from_callback,
    set_language,
    start,
)
from dnd_helper_bot.handlers.monsters import (
    monster_detail,
    monster_random,
    monster_search_prompt,
    monsters_filter_action,
    monsters_list,
)
from dnd_helper_bot.handlers.search import handle_search_text
from dnd_helper_bot.handlers.spells import (
    spell_detail,
    spell_random,
    spell_search_prompt,
    spells_filter_action,
    spells_list,
)
from dnd_helper_bot.logging_config import configure_logging


async def _on_error(update, context) -> None:
    """Global error handler: log full traceback without raising."""
    log = logging.getLogger("dnd_helper_bot.errors")
    try:
        err = getattr(context, "error", None)
        exc_info = (type(err), err, getattr(err, "__traceback__", None)) if err else True
        log.error("Unhandled error in update handler", exc_info=exc_info)
    except Exception:
        try:
            log.error("Unhandled error (fallback)")
        except Exception:
            pass


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    configure_logging(service_name=os.getenv("LOG_SERVICE_NAME", "bot"))

    application = ApplicationBuilder().token(token).build()

    # Register global error handler
    application.add_error_handler(_on_error)

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search_text))

    application.add_handler(CallbackQueryHandler(dice_roll, pattern=r"^dice:(d20|d6|2d6|custom)$"))
    application.add_handler(CallbackQueryHandler(show_dice_menu_from_callback, pattern=r"^menu:dice$"))

    application.add_handler(CallbackQueryHandler(monsters_list, pattern=r"^monster:list:page:\d+$"))
    application.add_handler(CallbackQueryHandler(monster_detail, pattern=r"^monster:detail:\d+$"))
    application.add_handler(CallbackQueryHandler(monster_random, pattern=r"^monster:random$"))
    application.add_handler(
        CallbackQueryHandler(monster_search_prompt, pattern=r"^monster:search$")
    )
    application.add_handler(CallbackQueryHandler(monsters_filter_action, pattern=r"^mflt:"))

    application.add_handler(CallbackQueryHandler(spells_list, pattern=r"^spell:list:page:\d+$"))
    application.add_handler(CallbackQueryHandler(spell_detail, pattern=r"^spell:detail:\d+$"))
    application.add_handler(CallbackQueryHandler(spell_random, pattern=r"^spell:random$"))
    application.add_handler(CallbackQueryHandler(spell_search_prompt, pattern=r"^spell:search$"))
    application.add_handler(CallbackQueryHandler(spells_filter_action, pattern=r"^sflt:"))
    application.add_handler(CallbackQueryHandler(show_bestiarie_menu_from_callback, pattern=r"^menu:monsters$"))
    application.add_handler(CallbackQueryHandler(show_spells_menu_from_callback, pattern=r"^menu:spells$"))
    application.add_handler(CallbackQueryHandler(show_settings_from_callback, pattern=r"^menu:settings$"))
    application.add_handler(CallbackQueryHandler(set_language, pattern=r"^lang:set:(ru|en)$"))

    application.add_handler(
        CallbackQueryHandler(show_main_menu_from_callback, pattern=r"^menu:main$")
    )

    application.run_polling()


if __name__ == "__main__":
    asyncio.run(main())


