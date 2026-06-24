# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/). This project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.1] - 2026-06-24

### Changed

- **BREAKING — project renamed `telek` → `telegram-agent`.** The
  distribution (PyPI) name is now `telegram-agent`, the import package is
  `telegram_agent` (e.g. `from telegram_agent.cli import main`), and the
  CLI command is `telegram-agent` (e.g. `telegram-agent bot send`). The
  `python -m telegram_agent` module entry point follows the package name.
- Environment-variable prefix `TELEK_` → `TELEGRAM_AGENT_`
  (`TELEGRAM_AGENT_BOT_TOKEN`, `TELEGRAM_AGENT_LIVE_TEST_USER_CHAT`,
  `TELEGRAM_AGENT_LIVE_TEST_GROUP_CHAT`). Update local `.env` files and
  CI/repo secrets accordingly.
- GitHub repo (`agentculture/telegram-agent`), SonarCloud project key
  (`agentculture_telegram-agent`), and the agent nick / GitHub signature
  (`- telegram-agent (Claude)`) all updated to the new name.

### Migration

- Reinstall under the new name: `pip install telegram-agent` (or
  `uv sync`). Rewrite imports `telek` → `telegram_agent`, replace the
  `telek` command with `telegram-agent`, and rename any `TELEK_*`
  environment variables to `TELEGRAM_AGENT_*`.

## [0.3.0] - 2026-06-23

### Added

- **Vendored the `remember` + `recall` memory skills from eidetic-cli**
  (cite-don't-import) — the write/read halves of eidetic's shared
  `~/.eidetic/memory` surface, so this agent (Claude and its colleague backend)
  can persist facts across sessions and recall them later, sharing one store.
  `remember` drives `eidetic remember` (idempotent upsert of one JSON record or
  an NDJSON batch on stdin, dedup by id + content hash); `recall` drives
  `eidetic recall` with four search modes — exact / approximate / keyword /
  hybrid — each hit carrying text, full provenance metadata, a relevance score,
  and a freshness signal. The `.sh` wrappers are byte-verbatim from eidetic-cli
  (their first-party origin); each `SKILL.md` is localized only in the
  illustrative `--scope <nick>` examples (Provenance keeps "First-party to
  eidetic-cli"). Both default to this agent's PRIVATE scope, reading the suffix
  from `culture.yaml`. Runtime dep: the `eidetic` CLI on PATH (else a local
  eidetic-cli checkout with `uv`). Propagated by rollout-cli's `eidetic-memory`
  recipe.

## [0.2.0] - 2026-05-18

### Added

- Telegram surface (Bot API): `telegram-agent bot send`, `telegram-agent group roster`,
  `telegram-agent group pin`. Writes are dry-run by default; pass `--apply` to
  commit. Validated-preview dry-run runs `getMe`/`getChat`/
  `getChatMember` (plus per-verb permission asserts) before printing the
  plan, so foot-guns (invalid chat, missing permission, locked group)
  surface before any side effect.
- `TELEGRAM_AGENT_BOT_TOKEN` loading from environment or `.env` (cwd, then nearest
  git root; process env always wins). World-writable `.env` files are
  skipped with a warning.
- Vendored `.claude/skills/telegram/` agent wrapper (SKILL.md + send/roster/
  pin scripts).
- New optional dependency: `python-telegram-bot>=21,<22` under
  `[project.optional-dependencies] telegram`. Core install stays
  zero-dep; install with `pip install 'telegram-agent[telegram]'`.
- Live smoke tests (`tests/test_telegram_live.py`, marker `live`) covering
  the full `bot send` / `group roster` / `group pin` cycle against the
  real Telegram Bot API. Gated on `TELEGRAM_AGENT_LIVE_TEST_USER_CHAT` and
  `TELEGRAM_AGENT_LIVE_TEST_GROUP_CHAT`; skipped automatically when either is
  unset.
- `live-smoke` CI job in `.github/workflows/tests.yml` that runs the live
  suite against repo secrets (`TELEGRAM_AGENT_BOT_TOKEN`, `TELEGRAM_AGENT_LIVE_TEST_USER_CHAT`,
  `TELEGRAM_AGENT_LIVE_TEST_GROUP_CHAT`). Gated on the token's presence so fork PRs
  and unconfigured repos are a no-op rather than a hard fail.

### Notes

- `group roster` is bot-only by design; the Bot API does not expose full
  member lists. The response includes a `limits.note` reminding callers.
  MTProto support is deferred.

## [0.1.0] - 2026-05-18

### Added

- Initial sibling-scaffold per [agentculture/telegram-agent#1](https://github.com/agentculture/telegram-agent/issues/1):
  Python package layout with universal agent-affordance verbs (`telegram-agent learn`,
  `telegram-agent explain`, `telegram-agent whoami`); structured `TelegramAgentError` + `--json` output;
  vendored baseline skills (`cicd`, `communicate`, `run-tests`, `sonarclaude`,
  `version-bump`) from `agentculture/steward`; CI (`tests.yml` with
  pytest+coverage+lint+SonarCloud-gated scan+`version-check`, `publish.yml`
  with Trusted Publishing to TestPyPI/PyPI); `sonar-project.properties` and
  `culture.yaml` declaring `telegram-agent` as the agent nick.
