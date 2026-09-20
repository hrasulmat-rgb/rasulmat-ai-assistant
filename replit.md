# Python Telegram Bot

A small Telegram bot that responds to `/start`, `/help`, and OpenAI-powered text prompts.

## Run & Operate

- `python telegram-bot/bot.py` — run the Telegram bot
- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required secret: `TELEGRAM_BOT_TOKEN` — Telegram bot token from BotFather
- Required secret: `OPENAI_API_KEY` — OpenAI API key
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
- `telegram-bot/requirements.txt` — Python dependency
- `telegram-bot/README.md` — setup and run instructions

## Architecture decisions

- The bot uses long polling, which works without exposing a public webhook URL.
- Telegram and OpenAI credentials are read from Replit Secrets and never stored in source code.

## Product

The bot greets users, explains its commands, and returns OpenAI responses to regular text messages.

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

_Populate as you build — sharp edges, "always run X before Y" rules._

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
