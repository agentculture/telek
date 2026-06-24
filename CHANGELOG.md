# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/). This project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-06-24

### Added

- **Memory-discipline "Conventions and workflow" section in `CLAUDE.md`** — a
  per-task *recall-before / remember-after* convention (scope localized to this
  repo's nick) so the vendored `remember` / `recall` skills are actually used,
  not just present: `/recall` before non-trivial work to build on prior
  decisions instead of re-deriving them, and `/remember` when a non-obvious
  decision, constraint, fix-and-why, or hard-won gotcha surfaces. The section
  documents this repo's memory as **in-repo and public** — records resolve to
  `<repo-root>/.eidetic/memory` (committed, team- and mesh-shared). Inserted
  idempotently (skipped if already present), slotted under an existing
  "Conventions and workflow" heading when one exists, else appended.

### Changed

- **Refreshed the `remember` + `recall` wrappers from eidetic-cli 0.10.0**
  (cite-don't-import) — picks up eidetic's **project-local store default**: the
  files backend now resolves per record by visibility — PUBLIC records inside a
  git repo go to `<repo-root>/.eidetic/memory` (committed, team-shared), PRIVATE
  records (or any record outside a repo) go to `$HOME/.eidetic/memory` (never
  committed), an explicit `EIDETIC_DATA_DIR` still wins, and recall reads both
  stores and merges. Also carries the 0.9.3 hardening (interactive-stdin guard,
  `help` as a search term, SIGPIPE-safe suffix parsing). **Recipe policy
  override (the wrappers here are NOT byte-verbatim):** the injected default
  visibility is flipped from eidetic's `private` to **`public`**, so a plain
  `/remember` lands the note in `./.eidetic/memory` in this repo, kept as part
  of the repo — pass `--visibility private` to route a record to `$HOME`
  instead. `remember` drives `eidetic remember` (idempotent upsert of one JSON
  record or an NDJSON batch on stdin); `recall` drives `eidetic recall` with
  four search modes (exact / approximate / keyword / hybrid). Each `SKILL.md` is
  localized only in the illustrative `--scope <nick>` examples (Provenance keeps
  "First-party to eidetic-cli"). Runtime dep: the `eidetic` CLI on PATH (else a
  local eidetic-cli checkout with `uv`) — **`eidetic >= 0.10.0`** for the
  in-repo routing; on an older CLI the public records still work but are stored
  in `$HOME/.eidetic/memory` instead of in-repo. Propagated by rollout-cli's
  `eidetic-memory` recipe.

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
- Live smoke tests (`tests/test_telegram_live.py`, marker `live`) covering
  the full `bot send` / `group roster` / `group pin` cycle against the
  real Telegram Bot API. Gated on `TELEK_LIVE_TEST_USER_CHAT` and
  `TELEK_LIVE_TEST_GROUP_CHAT`; skipped automatically when either is
  unset.
- `live-smoke` CI job in `.github/workflows/tests.yml` that runs the live
  suite against repo secrets (`TELEK_BOT_TOKEN`, `TELEK_LIVE_TEST_USER_CHAT`,
  `TELEK_LIVE_TEST_GROUP_CHAT`). Gated on the token's presence so fork PRs
  and unconfigured repos are a no-op rather than a hard fail.

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
