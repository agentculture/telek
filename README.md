# telek

**Agent-first Telegram community management tools.**

`telek` is an [AgentCulture](https://github.com/agentculture) sibling repo.
The shape it wears — pyproject layout, CLI conventions, vendored skills, CI
pipeline — comes from
[`steward`'s sibling pattern](https://github.com/agentculture/steward/blob/main/docs/sibling-pattern.md).

## Status

**Alpha.** v0.2 lands the Telegram surface: `telek bot send`,
`telek group roster`, `telek group pin`. Every write verb is dry-run by
default; pass `--apply` to commit.

## Install

```bash
uv tool install telek
```

Then `telek --version` should work on your PATH. `uv tool install` is the
supported path — not `pip install`.

## Usage

```bash
telek learn               # structured self-teaching prompt for an agent
telek learn --json        # same, as a JSON payload
telek explain             # top-level overview
telek explain whoami      # per-verb markdown
telek whoami              # nick + version + bot-token-configured probe
telek whoami --json       # structured payload
```

Every command supports `--json` where it produces a listing or report,
and respects the exit-code policy (`0` success / `1` user error / `2` env
error). Errors carry a `{code, message, remediation}` shape; text mode
renders as `error: ...` + `hint: ...` on stderr.

### Telegram verbs (requires `pip install 'telek[telegram]'`)

```bash
# read-only: count + admins + bot's own permissions
telek group roster --chat @announcements --json

# write (dry-run by default; --apply to commit)
telek bot send --chat @announcements --text "hello" --parse-mode markdown
telek bot send --chat @announcements --text "hello" --apply

# pin / unpin (also dry-run by default)
telek group pin --chat @announcements --message 123 --apply
telek group pin --chat @announcements --unpin --apply
```

## Configuration

| Variable           | Purpose                                                        |
|--------------------|----------------------------------------------------------------|
| `TELEK_BOT_TOKEN`  | Telegram bot token. Required for write verbs once they land. Never logged. |

Bot tokens, group IDs, and webhook secrets **must never** be committed to
the repo — keep them in repo secrets or a git-ignored `.env`.

Tokens are loaded from `os.environ` first, then from a `.env` file in the
current directory, then from a `.env` at the nearest enclosing git root.
Process env always wins. `.env` files that are world-writable on POSIX are
skipped with a warning.

## Testing

The unit suite runs offline. Run it with:

```bash
uv run pytest -v
```

### Live smoke tests

Optional live tests in `tests/test_telegram_live.py` exercise `bot send` /
`group roster` / `group pin` / unpin against the real Bot API. Enable by
exporting two numeric chat IDs the bot can reach:

```bash
export TELEK_LIVE_TEST_USER_CHAT=<numeric user chat_id>
export TELEK_LIVE_TEST_GROUP_CHAT=<numeric group chat_id>
uv run pytest tests/test_telegram_live.py -v
```

The bot must be a member of the user DM (the user must have started a
chat with the bot) and a member-admin (with **Pin Messages**) in the
group. CI does not set these env vars, so live tests skip in CI.

## Project shape

See [`CLAUDE.md`](./CLAUDE.md) for the directory layout, build / test /
publish commands, and the sibling-pattern conventions telek inherits.

## Contributing

Every PR must bump the version in `pyproject.toml` and prepend a
[Keep a Changelog](https://keepachangelog.com/) entry to `CHANGELOG.md`.
The `version-check` CI job enforces this. Use the vendored `version-bump`
skill:

```bash
python .claude/skills/version-bump/scripts/bump.py patch  # or minor / major
```
