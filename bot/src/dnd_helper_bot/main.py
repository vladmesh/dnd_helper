import os
import asyncio

from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from dnd_helper_bot.handlers.menu import start
from dnd_helper_bot.handlers.search import handle_search_text
from dnd_helper_bot.handlers.dice import dice_roll
from dnd_helper_bot.handlers.monsters import (
    monsters_list,
    monster_detail,
    monster_random,
    monster_search_prompt,
)
from dnd_helper_bot.handlers.spells import (
    spells_list,
    spell_detail,
    spell_random,
    spell_search_prompt,
)


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search_text))

    application.add_handler(CallbackQueryHandler(dice_roll, pattern=r"^dice:(d20|d6|2d6)$"))

    application.add_handler(CallbackQueryHandler(monsters_list, pattern=r"^monster:list:page:\d+$"))
    application.add_handler(CallbackQueryHandler(monster_detail, pattern=r"^monster:detail:\d+$"))
    application.add_handler(CallbackQueryHandler(monster_random, pattern=r"^monster:random$"))
    application.add_handler(CallbackQueryHandler(monster_search_prompt, pattern=r"^monster:search$"))

    application.add_handler(CallbackQueryHandler(spells_list, pattern=r"^spell:list:page:\d+$"))
    application.add_handler(CallbackQueryHandler(spell_detail, pattern=r"^spell:detail:\d+$"))
    application.add_handler(CallbackQueryHandler(spell_random, pattern=r"^spell:random$"))
    application.add_handler(CallbackQueryHandler(spell_search_prompt, pattern=r"^spell:search$"))

    application.run_polling()


if __name__ == "__main__":
    asyncio.run(main())


