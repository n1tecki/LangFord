# interfaces/telegram_bot.py
import os
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)
from dotenv import load_dotenv

from core.langford_service import init_langford, run_langford

load_dotenv()
logging.basicConfig()
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello, I am your Langford agent on Telegram.\n"
        "Send 'brief' to get your daily executive brief."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text
    logger.info("Message: %s", text)
    try:
        reply = run_langford(text)
    except Exception:
        logger.exception("Error while running Langford:")
        reply = "Something went wrong in the backend. Please try again in a moment."
    await update.message.reply_text(reply)


def main():
    init_langford()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("Please set TELEGRAM_BOT_TOKEN.")

    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()


if __name__ == "__main__":
    main()
