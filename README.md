# telek

**Agent-first Telegram community management tools.**

`telek` is an [AgentCulture](https://github.com/agentculture) sibling repo.
The shape it wears — pyproject layout, CLI conventions, vendored skills, CI
pipeline — comes from
[`steward`'s sibling pattern](https://github.com/agentculture/steward/blob/main/docs/sibling-pattern.md).

## Status

**Alpha — scaffold only.** Today the CLI exposes the universal
agent-affordance verbs (`learn`, `explain`, `whoami`). The Telegram surface
(`telek bot ...`, `telek group ...`) lands in a follow-up PR; every write
verb there will default to dry-run with an explicit `--apply` flag.

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

## Configuration

| Variable           | Purpose                                                        |
|--------------------|----------------------------------------------------------------|
| `TELEK_BOT_TOKEN`  | Telegram bot token. Required for write verbs once they land. Never logged. |

Bot tokens, group IDs, and webhook secrets **must never** be committed to
the repo — keep them in repo secrets or a git-ignored `.env`.

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
