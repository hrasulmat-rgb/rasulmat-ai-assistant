"""A small Telegram bot that sends text messages to OpenAI."""

import logging
import os

from openai import AsyncOpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Welcome a user when they start the bot."""
    del context
    user = update.effective_user
    name = user.first_name if user else "there"
    await update.message.reply_text(
        f"Hi {name}! I’m ready to help.\n\n"
        "Send me any message and I’ll ask OpenAI for a response. Use /help to see the available commands."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the commands supported by this bot."""
    del context
    await update.message.reply_text(
        "Available commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n\n"
        "Send me any text and I’ll ask OpenAI for a response."
    )


def split_message(text: str, limit: int = 4000) -> list[str]:
    """Split long responses into Telegram-safe message chunks."""
    return [text[index : index + limit] for index in range(0, len(text), limit)]


async def ask_openai(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a user's text to OpenAI and return the generated response."""
    if not update.message or not update.message.text:
        return

    client: AsyncOpenAI = context.application.bot_data["openai_client"]
    await update.message.chat.send_action("typing")

    try:
        response = await client.responses.create(
            model="gpt-5-mini",
            input=update.message.text,
        )
        answer = response.output_text.strip()
    except Exception:
        logger.exception("OpenAI request failed")
        await update.message.reply_text(
            "I couldn’t get a response right now. Please try again in a moment."
        )
        return

    if not answer:
        await update.message.reply_text("OpenAI returned an empty response. Please try again.")
        return

    for message in split_message(answer):
        await update.message.reply_text(message)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors without exposing implementation details to chat users."""
    logger.error("Telegram update failed: %s", context.error, exc_info=context.error)


def main() -> None:
    """Build the application and start long polling."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set. Add it as a Replit Secret or export it "
            "before starting the bot."
        )

    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it as a Replit Secret or export it "
            "before starting the bot."
        )

    application = Application.builder().token(token).build()
    application.bot_data["openai_client"] = AsyncOpenAI(api_key=openai_api_key)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ask_openai))
    application.add_error_handler(error_handler)

    logger.info("Bot is running. Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()