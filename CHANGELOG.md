# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/). This project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-05-18

### Added

- Telegram surface (Bot API): `telek bot send`, `telek group roster`,
  `telek group pin`. Writes are dry-run by default; pass `--apply` to
  commit. Validated-preview dry-run runs `getMe`/`getChat`/
  `getChatMember` (plus per-verb permission asserts) before printing the
  plan, so foot-guns (invalid chat, missing permission, locked group)
  surface before any side effect.
- `TELEK_BOT_TOKEN` loading from environment or `.env` (cwd, then nearest
  git root; process env always wins). World-writable `.env` files are
  skipped with a warning.
- Vendored `.claude/skills/telegram/` agent wrapper (SKILL.md + send/roster/
  pin scripts).
- New optional dependency: `python-telegram-bot>=21,<22` under
  `[project.optional-dependencies] telegram`. Core install stays
  zero-dep; install with `pip install 'telek[telegram]'`.

### Notes

- `group roster` is bot-only by design; the Bot API does not expose full
  member lists. The response includes a `limits.note` reminding callers.
  MTProto support is deferred.

## [0.1.0] - 2026-05-18

### Added

- Initial sibling-scaffold per [agentculture/telek#1](https://github.com/agentculture/telek/issues/1):
  Python package layout with universal agent-affordance verbs (`telek learn`,
  `telek explain`, `telek whoami`); structured `TelekError` + `--json` output;
  vendored baseline skills (`cicd`, `communicate`, `run-tests`, `sonarclaude`,
  `version-bump`) from `agentculture/steward`; CI (`tests.yml` with
  pytest+coverage+lint+SonarCloud-gated scan+`version-check`, `publish.yml`
  with Trusted Publishing to TestPyPI/PyPI); `sonar-project.properties` and
  `culture.yaml` declaring `telek` as the agent nick.
