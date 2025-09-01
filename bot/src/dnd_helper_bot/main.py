import asyncio
import os

from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from dnd_helper_bot.handlers.dice import dice_roll, show_dice_menu_from_callback
from dnd_helper_bot.handlers.menu import show_main_menu_from_callback, start, show_bestiarie_menu_from_callback, show_spells_menu_from_callback
from dnd_helper_bot.handlers.monsters import (
    monster_detail,
    monster_random,
    monster_search_prompt,
    monsters_list,
    monsters_filter_action,
)
from dnd_helper_bot.handlers.search import handle_search_text
from dnd_helper_bot.handlers.spells import (
    spell_detail,
    spell_random,
    spell_search_prompt,
    spells_list,
    spells_filter_action,
)
from dnd_helper_bot.logging_config import configure_logging


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    configure_logging(service_name=os.getenv("LOG_SERVICE_NAME", "bot"))

    application = ApplicationBuilder().token(token).build()

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

    application.add_handler(
        CallbackQueryHandler(show_main_menu_from_callback, pattern=r"^menu:main$")
    )

    application.run_polling()


if __name__ == "__main__":
    asyncio.run(main())


