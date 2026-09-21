"""A small Telegram bot that sends text messages to Gemini."""

import logging
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from google import genai
from google.genai import types
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from memory import ConversationStore
from document_processing import (
    AttachmentError,
    ProcessedAttachment,
    compact_for_memory,
    extension_for,
    process_attachment,
    validate_size,
)


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

SYSTEM_INSTRUCTION = """You are Rasulmat AI Assistant, a professional personal assistant.
Your primary language is Uzbek, but you can work fluently in Russian and English.
Answer in the same language the user writes in unless asked otherwise.
Be concise, practical and accurate.
You are especially useful for banking work, corporate clients, official letters, business correspondence, document analysis, calculations, translations and preparing structured information.
When writing official documents, use professional business language.
Do not invent facts when information is missing; ask for the missing information.
For simple questions, give short direct answers.
For complex tasks, provide a clear and structured answer."""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Welcome a user when they start the bot."""
    del context
    user = update.effective_user
    name = user.first_name if user else "there"
    await update.message.reply_text(
        f"Hi {name}! I’m ready to help.\n\n"
        "Send me any message and I’ll ask Gemini for a response. "
        "Use /help to see the available commands. Your conversation memory is saved "
        "for your Telegram account."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the commands supported by this bot."""
    del context
    await update.message.reply_text(
        "Available commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n\n"
        "/memory - Show the number of saved messages\n"
        "/newchat - Clear your conversation after confirmation\n\n"
        "Send me any text and I’ll ask Gemini for a response."
    )


def split_message(text: str, limit: int = 4000) -> list[str]:
    """Split long responses into Telegram-safe message chunks."""
    return [text[index : index + limit] for index in range(0, len(text), limit)]


async def ask_gemini(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a user's text to Gemini and return the generated response."""
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    if not user:
        return

    client: genai.Client = context.application.bot_data["gemini_client"]
    memory: ConversationStore = context.application.bot_data["memory_store"]
    history = memory.recent_messages(user.id)
    contents = history_to_contents(history)
    contents.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=update.message.text)],
        )
    )
    memory.add_message(user.id, "user", update.message.text)
    await update.message.chat.send_action("typing")

    try:
        response = await client.aio.models.generate_content(
            model="gemini-3.6-flash",
            contents=contents,
            config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION),
        )
        answer = (response.text or "").strip()
    except Exception as error:
        error_text = str(error).lower()
        logger.exception("Gemini request failed")
        if "quota" in error_text or "resource_exhausted" in error_text or "rate limit" in error_text:
            await update.message.reply_text(
                "Gemini’s free-tier quota has been reached. Please try again later "
                "or check your Gemini API quota."
            )
        elif "api key" in error_text or "unauthorized" in error_text or "permission" in error_text:
            await update.message.reply_text(
                "Gemini rejected the configured API key. Please update the "
                "GEMINI_API_KEY Replit Secret."
            )
        else:
            await update.message.reply_text(
                "I couldn’t get a Gemini response right now. Please try again in a moment."
            )
        return

    if not answer:
        await update.message.reply_text("Gemini returned an empty response. Please try again.")
        return

    memory.add_message(user.id, "assistant", answer)
    for message in split_message(answer):
        await update.message.reply_text(message)


def history_to_contents(history: list) -> list[types.Content]:
    """Convert saved messages to Gemini's user/model conversation roles."""
    return [
        types.Content(
            role="user" if message.role == "user" else "model",
            parts=[types.Part.from_text(text=message.content)],
        )
        for message in history
    ]


def attachment_prompt(attachment: ProcessedAttachment, question: str) -> str:
    """Build the text instruction that accompanies an uploaded attachment."""
    prompt = (
        f"The user uploaded a file named {attachment.display_name}. "
        f"Answer the user's request about this file: {question}"
    )
    if attachment.extracted_text:
        prompt += (
            "\n\nExtracted local text and table data follows. Treat it as source material, "
            "preserve exact numbers, dates, account numbers and totals, and do not invent "
            "missing information:\n\n"
            f"{attachment.extracted_text}"
        )
    if not question.strip():
        prompt += (
            "\n\nGive a concise summary first, then ask what the user wants to do with "
            "the file."
        )
    return prompt


async def handle_attachment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Download, analyze, remember, and remove one Telegram attachment."""
    if not update.message:
        return
    user = update.effective_user
    if not user:
        return

    document = update.message.document
    photo = update.message.photo[-1] if update.message.photo else None
    if document:
        display_name = Path(document.file_name or "uploaded_file").name
        file_id = document.file_id
        file_size = document.file_size
    elif photo:
        display_name = "uploaded_image.jpg"
        file_id = photo.file_id
        file_size = photo.file_size
    else:
        return

    try:
        extension_for(display_name)
        validate_size(file_size)
    except AttachmentError as error:
        await update.message.reply_text(str(error))
        return

    question = (update.message.caption or "").strip()
    if not question:
        question = "Provide a concise summary and ask what I want to do with this file."

    memory: ConversationStore = context.application.bot_data["memory_store"]
    client: genai.Client = context.application.bot_data["gemini_client"]

    try:
        telegram_file = await context.bot.get_file(file_id)
        with TemporaryDirectory(prefix="telegram-attachment-") as directory:
            path = Path(directory) / display_name
            await telegram_file.download_to_drive(custom_path=path)
            attachment = process_attachment(path, display_name)
            history = memory.recent_messages(user.id)
            contents = history_to_contents(history)
            prompt = attachment_prompt(attachment, question)
            parts = [types.Part.from_text(text=prompt)]
            if attachment.multimodal:
                parts.append(types.Part.from_bytes(data=path.read_bytes(), mime_type=attachment.mime_type))
            contents.append(types.Content(role="user", parts=parts))

            memory_input = (
                f"[Uploaded file: {attachment.display_name}]\n"
                f"User request: {question}\n"
                f"Saved extracted context for follow-up questions:\n"
                f"{compact_for_memory(attachment.extracted_text)}"
            )
            memory.add_message(user.id, "user", memory_input)
            await update.message.chat.send_action("typing")
            response = await client.aio.models.generate_content(
                model="gemini-3.6-flash",
                contents=contents,
                config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION),
            )
            answer = (response.text or "").strip()
            if not answer:
                await update.message.reply_text(
                    "Gemini returned an empty response for this file. Please try again."
                )
                return

            memory.add_message(user.id, "assistant", answer)
            for message in split_message(answer):
                await update.message.reply_text(message)
    except AttachmentError as error:
        await update.message.reply_text(str(error))
    except Exception:
        logger.exception("Attachment processing failed")
        await update.message.reply_text(
            "I couldn’t process this file right now. Check that it is valid and try again."
        )


async def memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tell the user how many messages are saved in their current conversation."""
    user = update.effective_user
    if not update.message or not user:
        return

    memory: ConversationStore = context.application.bot_data["memory_store"]
    count = memory.count_messages(user.id)
    await update.message.reply_text(
        f"Your current conversation has {count} saved message"
        f"{'' if count == 1 else 's'}."
    )


async def new_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ask the user to confirm clearing only their own conversation."""
    del context
    user = update.effective_user
    if not update.message or not user:
        return

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Clear memory",
                    callback_data=f"newchat:confirm:{user.id}",
                ),
                InlineKeyboardButton(
                    "Cancel",
                    callback_data=f"newchat:cancel:{user.id}",
                ),
            ]
        ]
    )
    await update.message.reply_text(
        "Clear your saved conversation history? This only affects your Telegram account.",
        reply_markup=keyboard,
    )


async def new_chat_confirmation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Apply or cancel a /newchat request after button confirmation."""
    query = update.callback_query
    if not query or not query.data:
        return

    action, target_user_id = query.data.split(":")[1:]
    if query.from_user.id != int(target_user_id):
        await query.answer("Only the user who requested this can confirm it.", show_alert=True)
        return

    await query.answer()
    if action == "confirm":
        memory: ConversationStore = context.application.bot_data["memory_store"]
        memory.clear_user_history(query.from_user.id)
        await query.edit_message_text("Your conversation memory has been cleared.")
    else:
        await query.edit_message_text("Your conversation memory was kept.")


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

    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it as a Replit Secret or export it "
            "before starting the bot."
        )

    memory = ConversationStore(
        Path(__file__).with_name("data") / "conversations.sqlite3"
    )
    memory.initialize()

    application = Application.builder().token(token).build()
    application.bot_data["gemini_client"] = genai.Client(api_key=gemini_api_key)
    application.bot_data["memory_store"] = memory
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("memory", memory_command))
    application.add_handler(CommandHandler("newchat", new_chat_command))
    application.add_handler(
        CallbackQueryHandler(new_chat_confirmation, pattern=r"^newchat:(confirm|cancel):\d+$")
    )
    application.add_handler(MessageHandler(filters.PHOTO, handle_attachment))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_attachment))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ask_gemini))
    application.add_error_handler(error_handler)

    logger.info("Bot is running. Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()