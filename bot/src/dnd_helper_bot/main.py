import os
import asyncio
from telegram.ext import Application, CommandHandler


async def start(update, context):
    await update.message.reply_text("DnD Helper bot is running")


async def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))

    await application.run_polling()


if __name__ == "__main__":
    asyncio.run(main())


