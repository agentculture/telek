# Telegram integration (v0.2)

**Status:** Design — approved through brainstorming, awaiting written review.
**Author:** telek (Claude)
**Date:** 2026-05-18
**Target version:** `0.2.0`
**Tracks roadmap item:** v0.2 — "Telegram surface: `telek bot send`, `telek group roster`,
`telek group pin`. Brings `python-telegram-bot` as the first runtime dependency. Every write
verb dry-run by default."

## 1. Summary

Land the three verbs named in the v0.2 roadmap behind a single sync façade over
`python-telegram-bot`. Writes (`send`, `pin`) are dry-run by default and require `--apply`
to commit; dry-run hits read-only Bot API methods to produce a validated plan, so foot-guns
(invalid chat, missing bot permission, locked group) surface before any user-visible side
effect. A vendored `.claude/skills/telegram/` wraps the verbs so agents have a documented,
JSON-shaped surface to call.

Bot API limitations are honored, not papered over: `group roster` returns member count plus
the administrator list plus the bot's own membership record, and is explicit in its JSON
payload that a full member list is not retrievable via the Bot API.

## 2. Scope

### In scope (v0.2)

- `telek bot send` — send a message to a chat / channel.
- `telek group roster` — list what the Bot API exposes about a group: count, admins,
  bot's own permissions.
- `telek group pin` — pin or unpin a message in a chat.
- `python-telegram-bot` as an **optional** runtime dependency
  (`pip install 'telek[telegram]'`); core `pip install telek` stays zero-dep.
- `TELEK_BOT_TOKEN` loading from environment or `.env` (process env wins).
- A vendored `.claude/skills/telegram/` skill mirroring the existing skill conventions.
- Validated-preview dry-run on writes (token required; no offline mode in v0.2).

### Out of scope (deferred)

- MTProto / user-account access (telethon, pyrogram) — would unlock full rosters but
  changes auth surface and risk profile; revisit in a later RFC.
- Scheduled announcements, moderation rules, `explain` catalog entries for the new verbs
  (v0.3+ per roadmap).
- Auto-retry on `RetryAfter` / `NetworkError` — surface clean errors instead.
- Structured logging / log files.
- Real-network integration tests in CI.
- `--offline` dry-run that skips the Bot API entirely.

## 3. Architecture

### 3.1 Module layout

```text
telek/
├── telegram/
│   ├── __init__.py            # re-exports TelegramClient, load_token, redact
│   ├── _client.py             # TelegramClient sync façade over python-telegram-bot
│   ├── _config.py             # load_token(), redact(), .env discovery
│   ├── _errors.py             # wrap(exc) -> TelekError mapping table
│   └── _plan.py               # ValidatedPlan dataclass + verb-specific intents
└── cli/_commands/
    ├── bot.py                 # `telek bot send`
    └── group.py               # `telek group roster`, `telek group pin`
```

### 3.2 Sync façade

`TelegramClient` exposes synchronous methods (`get_me`, `get_chat`, `get_chat_member`,
`get_chat_administrators`, `get_chat_member_count`, `send_message`, `pin_chat_message`,
`unpin_chat_message`). Each wraps a `python-telegram-bot` async call with `asyncio.run`.
This keeps CLI verbs synchronous (matching the existing learn / explain / whoami pattern)
and lets tests substitute a fake without touching asyncio.

### 3.3 Optional dependency

```toml
# pyproject.toml
[project.optional-dependencies]
telegram = ["python-telegram-bot>=21,<22"]
```

Importing `telek.telegram._client` succeeds without the lib installed; instantiating
`TelegramClient()` is what triggers the import, and any `ImportError` is caught and
re-raised as `TelekError(code=EXIT_ENV_ERROR, message="python-telegram-bot not
installed", remediation="pip install 'telek[telegram]'")`. CLI verbs only construct the
client after argparse succeeds, so `telek --help` / `telek learn` keep working without the
extra installed.

## 4. CLI surface

All three verbs are subcommands of new noun groups (`bot`, `group`) registered alongside
the existing `learn` / `explain` / `whoami` verbs. Targets accept either a numeric chat id
or `@username`; the parser normalizes to a single `--chat` string and the client resolves
it via `getChat`.

### 4.1 `telek bot send`

```text
telek bot send --chat <id|@name>
               (--text <s> | --text-stdin)
               [--parse-mode markdown|html|none]
               [--silent]
               [--reply-to <msg_id>]
               [--apply]
               [--json]
```

- Default = dry-run (validated preview). `--apply` is required to actually send.
- `--text` and `--text-stdin` are mutually exclusive; missing both is a user error.
- `--parse-mode` defaults to `none` (literal text). Markdown and HTML are opt-in to avoid
  entity-parsing foot-guns.
- `--silent` sets `disable_notification=True`.
- JSON shape on success:
  `{verb, chat: {id, type, title, username?}, message_id?, sent_at?, dry_run,
   intent: {text_preview, parse_mode, silent, reply_to?}, bot_self, warnings}`.

### 4.2 `telek group roster`

```text
telek group roster --chat <id|@name> [--json]
```

- Read-only; no `--apply`.
- JSON shape:
  `{verb, chat, member_count, administrators: [{user_id, username?, first_name, status,
   can_post?, can_pin?, can_invite?}], bot_self: {user_id, status, permissions},
   limits: {note: "Bot API does not expose full member list"}}`.
- Text mode renders a compact two-section view: chat metadata, then an admin table.

### 4.3 `telek group pin`

```text
telek group pin --chat <id|@name>
                [--message <msg_id>]
                [--silent]
                [--unpin]
                [--apply]
                [--json]
```

- Without `--unpin`, `--message` is required.
- With `--unpin` and no `--message`, the bot unpins the currently pinned message.
- Same dry-run default + `--apply` gating as `bot send`.
- JSON shape:
  `{verb, chat, action: "pin"|"unpin", message_id?, silent, dry_run,
   bot_self: {user_id, status, permissions}}`. Callers read `bot_self.permissions.can_pin`
  rather than a separate flag — `bot_self` is the same shape across all verbs.

### 4.4 Exit codes

Unchanged from existing policy: `0` success, `1` user error (missing flag, malformed
chat, missing permission), `2` env error (no token, lib not installed, network / API
failure, rate-limited). Every error carries `{code, message, remediation}` and is emitted
through `telek/cli/_output.py::emit_error`.

## 5. Authentication and configuration

### 5.1 Token loading

`telek/telegram/_config.py::load_token()` resolves `TELEK_BOT_TOKEN` from, in order:

1. Process environment (`os.environ`).
2. A `.env` file in the current working directory.
3. A `.env` file at the repo root (walking up from cwd to the nearest `.git`).

First match wins; process env always takes precedence over `.env` so CI exports cannot be
silently overridden.

### 5.2 `.env` parsing

In-house ~20-line parser, no `python-dotenv` runtime dependency. Supports `KEY=value`,
`KEY="value with spaces"`, blank lines, `#` comments. No interpolation, no multiline, no
`export`. Out-of-format lines are skipped with a single line in stderr in JSON mode.

The loader refuses to read `.env` files where world- or group-writable bits are set on
POSIX; it emits a non-fatal warning to stderr and skips the file. Windows skips the
permission check entirely.

`.env` is already in `.gitignore` from the existing scaffold.

### 5.3 Missing token

Required for every verb in v0.2 (all three hit the Bot API; there is no offline mode).
Missing token raises
`TelekError(EXIT_ENV_ERROR, "TELEK_BOT_TOKEN not set",
"set TELEK_BOT_TOKEN in your environment or a local .env file
(get the token from @BotFather)")`.

### 5.4 Redaction

A single chokepoint `_config.redact(s: str) -> str` masks any occurrence of the loaded
token before stdout, stderr, or `TelekError` messages cross the wire. Invariants:

- The token never appears in `--json` payloads (no token field is ever serialized).
- The token never appears in error messages — every `telegram.error.TelegramError` is
  caught at the client boundary and its `.message` is run through `redact()` before being
  wrapped into a `TelekError`.
- `telek whoami` reports "bot token configured" as a boolean — no length, no prefix, no
  last-N characters.

## 6. Validated-preview semantics

Every verb runs a fixed read-only probe sequence via `TelegramClient.validate(plan)
-> ValidatedPlan`; if any probe fails the verb stops with a `TelekError` and `--apply` is
never reached.

### 6.1 Shared probes (every verb)

1. `getMe()` — confirms the token is valid; yields `bot_self.user_id`. `401 Unauthorized`
   → `EXIT_ENV_ERROR` with remediation `"check TELEK_BOT_TOKEN — token rejected by
   Telegram"`.
2. `getChat(chat)` — resolves `--chat` into a `Chat` object (id, type, title, username).
   `400 Bad Request: chat not found` → `EXIT_USER_ERROR` with remediation `"verify chat
   id/username and that the bot is a member"`.
3. `getChatMember(chat, bot_self.user_id)` — confirms the bot is in the chat and yields
   its `status` plus permission flags.

### 6.2 Per-verb permission assertions

- **`bot send`** — requires `status ∈ {member, administrator, creator}`. Channels
  additionally require the bot's admin record to have `can_post_messages=True`. Groups
  whose `permissions.can_send_messages=False` fail with remediation `"group has messages
  disabled for non-admins; promote the bot or unlock the group"`.
- **`group pin`** — requires the bot to be an administrator with `can_pin_messages=True`.
  If the permission is missing the dry-run payload reports `bot_permissions:
  {can_pin: false}` and the verb fails before `--apply` is honored.
- **`group roster`** — only the shared probes; additionally calls
  `getChatMemberCount(chat)` and `getChatAdministrators(chat)` to populate the response.

### 6.3 `ValidatedPlan` shape

```python
@dataclass(frozen=True)
class ValidatedPlan:
    verb: str                       # "bot.send" | "group.pin" | "group.roster"
    chat: dict                      # {id, type, title, username?}
    bot_self: dict                  # {user_id, status, permissions}
    intent: dict                    # verb-specific (text_preview, message_id+action, ...)
    dry_run: bool                   # True for preview; False after --apply
    warnings: list[str]             # non-fatal (e.g. "channel has 0 subscribers")
```

`text_preview` is the message body truncated to 80 characters with a `…` suffix when
truncated. Full text is never re-emitted into JSON to keep payloads compact and
predictable.

### 6.4 Rate limits and retries

No retries in v0.2. `telegram.error.RetryAfter` surfaces as
`TelekError(EXIT_ENV_ERROR, "rate limited; retry after <n>s",
"wait and retry; v0.2 does not auto-retry")` with `n` taken from Telegram's payload.

## 7. Skill wrapper

```text
.claude/skills/telegram/
├── SKILL.md
└── scripts/
    ├── send.sh
    ├── roster.sh
    └── pin.sh
```

### 7.1 `SKILL.md`

Frontmatter `name: telegram` matching the directory name (per the repo's skills
convention). Content sections:

- **When to use** — bullets keyed off intent (announcing, moderating, auditing).
- **Prerequisites** — `pip install 'telek[telegram]'` plus `TELEK_BOT_TOKEN` in env or
  `.env`. Short walkthrough: create a bot with @BotFather, add it to the chat, promote it
  to admin for write verbs.
- **Verbs** — table mapping each script to the underlying `telek` invocation, with the
  dry-run / `--apply` contract in bold.
- **Recipes** — three canonical examples: send a markdown announcement; capture
  `message_id` from a prior send's JSON and pin it; print the admin list as a table.
- **Anti-patterns** — never store the token in repo files; review the dry-run JSON before
  `--apply`; do not poll roster (Bot API can't give full membership).

### 7.2 Scripts

Each script is thin and identical in shape, providing only:

1. `--json` by default piped through `jq` so agents get structured output without
   remembering the flag.
2. A one-second stderr warning before `--apply` on write verbs:
   `"sending real message to <chat title>; ctrl-c within 1s to abort"`. Tiny safety net
   for terminal use; not load-bearing in agent loops where `--apply` is deliberate.

Scripts require only `bash`, `jq`, and `telek` on `PATH`. `jq` is already a baseline
assumption (the sibling `communicate` skill uses it). No new tooling.

### 7.3 Signature handling

Telegram messages are not GitHub posts; the AgentCulture
`- <nick> (Claude)` signature rule does not auto-apply here. Recipes in `SKILL.md` note
this explicitly so agents do not append GitHub-style signatures by accident.

### 7.4 Provenance

`docs/skill-sources.md` gets a new row noting the `telegram` skill is original to telek
(not vendored from steward).

## 8. Error mapping

`telek/telegram/_errors.py::wrap(exc) -> TelekError` is the only place
`python-telegram-bot` exceptions cross into the rest of telek.

| `telegram.error` exception | Telek message | Remediation | Code |
|---|---|---|---|
| `InvalidToken`, `Unauthorized` | `"telegram rejected bot token"` | `"check TELEK_BOT_TOKEN with @BotFather"` | env (2) |
| `BadRequest("chat not found")` | `"chat not found: <chat>"` | `"verify id/username; ensure the bot is a member"` | user (1) |
| `BadRequest("not enough rights" \| "have no rights")` | `"bot lacks required permission: <verb-specific>"` | `"promote the bot and grant the needed permission"` | user (1) |
| `Forbidden("bot was kicked" \| "bot is not a member")` | `"bot is not in this chat"` | `"add the bot to the chat first"` | user (1) |
| `RetryAfter` | `"rate limited; retry after <n>s"` | `"wait and retry; v0.2 does not auto-retry"` | env (2) |
| `NetworkError`, `TimedOut` | `"network error talking to telegram"` | `"check connectivity and retry"` | env (2) |
| other `BadRequest` | passthrough (redacted) | empty | user (1) |
| any other `TelegramError` | passthrough (redacted) | empty | env (2) |

Every wrapped message passes through `_config.redact()`, so a token accidentally embedded
in an upstream error string never escapes.

## 9. Testing strategy

- **Fake client, not network mocks.** Tests inject a `FakeTelegramClient` that satisfies
  the same `TelegramClient` protocol — no `unittest.mock.patch` of `python-telegram-bot`
  internals. The fake stores recorded calls and returns canned `Chat` / `ChatMember` /
  `Message` dataclass instances. Tests stay fast and immune to library upgrades.
- **CLI smoke tests.** New `tests/test_telegram_cli.py` follows the existing `capsys`
  pattern in `tests/test_cli.py`. Cases: dry-run on every verb prints the validated plan
  without sending; `--apply` flips `dry_run=False` and calls the right client method;
  missing token → exit 2; unknown chat → exit 1; permission missing → exit 1 with the
  right remediation string; `bot send` requires `--text` or `--text-stdin`;
  `group pin --unpin --message X` and `group pin --unpin` (no message) both validate.
- **Redaction unit test.** `tests/test_redact.py` asserts the token never appears in
  stdout, stderr, JSON, or wrapped exception messages, including when substringed inside
  another string.
- **`.env` loader test.** Covers precedence (env wins), missing file (no-op), malformed
  line (skipped with warning), world-writable file (warning, file skipped).
- **Live network tests are out of scope for v0.2.** A future
  `tests/integration/test_telegram_live.py` gated on `TELEK_LIVE_TEST_CHAT` plus
  `TELEK_BOT_TOKEN` can land later; CI never runs it.
- **Coverage target.** Stays at the existing `fail_under = 60` in `pyproject.toml`.

## 10. Documentation and release

- README "Status" section updates to reflect that v0.2 has landed with the three verbs.
- README "Usage" section adds a Telegram subsection with `telek bot send --help`
  examples.
- README "Configuration" table adds `.env` precedence note.
- `CHANGELOG.md` gets a `[0.2.0]` entry per Keep-a-Changelog.
- `pyproject.toml` bumps to `0.2.0`; the existing `version-check` CI job enforces the
  bump.
- Trusted Publishing (`publish.yml`) ships `0.2.0` to PyPI on push to `main`.

## 11. Open questions

None blocking. The following are deferred to v0.3+ design notes:

- Whether to add `telek bot whoami-self` (Bot API `getMe` exposed as a verb) for
  diagnostics, or roll it into `telek whoami` when a token is present.
- Whether `roster --watch` (long-running) belongs as a CLI verb or a separate daemon.
- Whether the skill should grow a `bot-bootstrap.sh` that walks through @BotFather setup.
