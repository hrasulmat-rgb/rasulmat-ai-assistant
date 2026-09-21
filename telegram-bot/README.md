# Python Telegram Bot

A small Telegram bot built with `python-telegram-bot` and Google Gemini. It supports:

- `/start` — sends a welcome message
- `/help` — lists the available commands
- `/memory` — shows the number of saved messages in your current conversation
- `/newchat` — asks for confirmation before clearing only your conversation
- Any regular text — sends it to Gemini and returns the AI response
- PDF, DOCX, XLSX, XLS, TXT, CSV, JPG, and PNG uploads — extracts or analyzes the file with Gemini

Conversation history is stored in a local SQLite database at
`telegram-bot/data/conversations.sqlite3`. Each Telegram user has separate
history. The database keeps at most 200 messages per user. Only the most recent
20 messages, capped at 12,000 characters, are sent to Gemini for context.

Files up to 10 MB are accepted. Temporary downloads are removed after processing.
Document excerpts are retained in conversation memory so follow-up questions can
refer to the uploaded file.

## Run on Replit

The project has both required secrets configured:

- `TELEGRAM_BOT_TOKEN` — Telegram bot token from BotFather
- `GEMINI_API_KEY` — Google Gemini API key

To run the bot from the Shell:

```bash
python telegram-bot/bot.py
```

Keep the process running while you chat with the bot on Telegram.

## Run locally

1. Create a bot with [BotFather](https://t.me/BotFather) and copy its token.
2. Install the dependency:

   ```bash
   python -m pip install -r telegram-bot/requirements.txt
   ```

3. Export both secrets:

   ```bash
   export TELEGRAM_BOT_TOKEN="your-token"
   export GEMINI_API_KEY="your-gemini-api-key"
   ```

4. Start the bot:

   ```bash
   python telegram-bot/bot.py
   ```

Never commit real secrets or the SQLite database. Use `.env.example` as a
reference for the required environment variables.