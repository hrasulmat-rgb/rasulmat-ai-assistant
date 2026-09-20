# Python Telegram Bot

A small Telegram bot built with `python-telegram-bot`. It supports:

- `/start` — sends a welcome message
- `/help` — lists the available commands
- Any regular text — echoes the message back

## Run on Replit

The project already has a `TELEGRAM_BOT_TOKEN` secret configured. To run the bot
from the Shell:

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

3. Export the token:

   ```bash
   export TELEGRAM_BOT_TOKEN="your-token"
   ```

4. Start the bot:

   ```bash
   python telegram-bot/bot.py
   ```

Never commit the real token. Use `.env.example` as a reference for the required
environment variable.