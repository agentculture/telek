---
name: telegram
description: Send messages, inspect group rosters, and pin messages via the Telegram Bot API through `telegram-agent`. Writes are dry-run by default; --apply is required to commit.
---

# telegram skill

Thin wrapper around `telegram-agent bot send` / `telegram-agent group roster` / `telegram-agent group pin`.
Scripts default to `--json` so agents get structured output without
remembering the flag.

## When to use

- Announcing in a chat or channel the bot is a member of.
- Pinning an announcement after sending it (capture `message_id` from the
  send response and pass it to `pin`).
- Auditing who has admin permissions in a group, plus the bot's own
  permissions, before write operations.

## Prerequisites

1. `uv sync` in the telegram-agent repo root — installs the package and entry point.
   Alternatively, `pip install 'telegram-agent[telegram]'` for a global install.
   Scripts invoke `uv run telegram-agent` so `telegram-agent` does not need to be on `$PATH`.
2. `TELEGRAM_AGENT_BOT_TOKEN` in environment or a local `.env` (cwd or repo root).
   Get a token by creating a bot with `@BotFather` on Telegram.
3. The bot must be a member of the target chat. For pin and most channel
   send cases, the bot must be promoted to admin with the relevant
   permission (`can_pin_messages`, `can_post_messages`).

## Verbs

| Script | Wraps | Side effect | Default |
|---|---|---|---|
| `send.sh` | `telegram-agent bot send` | sends a message | **dry-run** — pass `--apply` to actually send |
| `roster.sh` | `telegram-agent group roster` | read-only | runs |
| `pin.sh` | `telegram-agent group pin` | pins / unpins | **dry-run** — pass `--apply` to actually pin |

## Recipes

### Announce, then pin

```bash
MSG_ID=$(./scripts/send.sh --chat @announcements --text "Release v0.2 is out" \
  --parse-mode markdown --apply | jq -r .message_id)
./scripts/pin.sh --chat @announcements --message "$MSG_ID" --apply
```

### Print the admin list

```bash
./scripts/roster.sh --chat @announcements | jq '.intent.administrators'
```

## Anti-patterns

- **Never** commit `TELEGRAM_AGENT_BOT_TOKEN` or `.env`. The `.gitignore` covers
  `.env`; keep it that way.
- **Always** read the dry-run JSON before passing `--apply`. The validated
  plan tells you if the bot has the right permissions; `--apply` skipping
  that check defeats the purpose.
- **Do not poll** roster to track membership — the Bot API doesn't expose
  full member lists; you'll only re-read the count.
- **No GitHub-style signature** in Telegram messages. The `- telegram-agent (Claude)`
  trailer applies to GitHub posts, not Telegram chat messages.
