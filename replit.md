# Python Telegram Bot

A small Telegram bot that responds to `/start`, `/help`, and Gemini-powered text prompts with per-user SQLite conversation memory.

## Run & Operate

- `python telegram-bot/bot.py` — run the Telegram bot
- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required secret: `TELEGRAM_BOT_TOKEN` — Telegram bot token from BotFather
- Required secret: `GEMINI_API_KEY` — Google Gemini API key
- Required env for the existing API scaffold: `DATABASE_URL` — Postgres connection string

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- API: Express 5
- DB: PostgreSQL + Drizzle ORM
- Validation: Zod (`zod/v4`), `drizzle-zod`
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)

## Where things live

- `telegram-bot/bot.py` — Telegram handlers and polling entry point
- `telegram-bot/memory.py` — SQLite conversation storage and bounded history selection
- `telegram-bot/requirements.txt` — Python dependency
- `telegram-bot/README.md` — setup and run instructions

## Architecture decisions

- The bot uses long polling, which works without exposing a public webhook URL.
- Telegram and Gemini credentials are read from Replit Secrets and never stored in source code.
- Conversation history is stored locally per Telegram user; only bounded recent history is sent to Gemini.

## Product

The bot greets users, explains its commands, returns Gemini responses, and supports per-user memory controls through `/memory` and `/newchat`.

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

_Populate as you build — sharp edges, "always run X before Y" rules._

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
