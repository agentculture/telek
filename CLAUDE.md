# CLAUDE.md

This file provides guidance to Claude Code when working in `telek`.

## Workspace layout

`telek` lives alongside its sibling repos in a shared workspace. Skills
that reach across siblings (e.g. `communicate`'s mesh-message helper) use
workspace-relative paths configured in `.claude/skills.local.yaml`.

## What telek is

Agent-first Telegram community management tools — moderation, roster
inspection, pinned-post hygiene, scheduled announcements. A sibling of
[`steward`](https://github.com/agentculture/steward) and other
AgentCulture agents; conforms to
[`docs/sibling-pattern.md`](https://github.com/agentculture/steward/blob/main/docs/sibling-pattern.md).

## Project shape

```text
telek/
├── telek/                       # Python package
│   ├── __init__.py              # __version__ via importlib.metadata
│   ├── __main__.py              # `python -m telek` entry
│   └── cli/
│       ├── __init__.py          # argparse root + _dispatch + main()
│       ├── _errors.py           # TelekError + EXIT_USER_ERROR / EXIT_ENV_ERROR
│       ├── _output.py           # emit_result / emit_error / emit_diagnostic
│       └── _commands/
│           ├── learn.py         # `telek learn`
│           ├── explain.py       # `telek explain <path>...`
│           └── whoami.py        # `telek whoami`
├── tests/
│   └── test_cli.py              # CLI smoke tests (capsys; no Click)
├── .claude/
│   ├── skills/                  # Vendored skills (cite, don't import)
│   │   ├── cicd/
│   │   ├── communicate/
│   │   ├── run-tests/
│   │   ├── sonarclaude/
│   │   └── version-bump/
│   └── skills.local.yaml.example  # Per-machine config template
├── .github/workflows/
│   ├── tests.yml                # pytest + coverage + lint + Sonar + version-check
│   └── publish.yml              # TestPyPI on PR, PyPI on push (Trusted Publishing)
├── docs/
│   └── skill-sources.md         # Upstream provenance for each vendored skill
├── pyproject.toml               # hatchling, Python ≥3.12, zero runtime deps
├── culture.yaml                 # agent nick + backend
├── sonar-project.properties     # SonarCloud project key
├── .flake8                      # line length 100, ignore E203 W503
├── .markdownlint-cli2.yaml      # repo-local markdownlint config
├── CHANGELOG.md                 # Keep-a-Changelog
└── README.md
```

## Build / test / publish commands

```bash
uv sync                                                       # install deps
uv run pytest -n auto --cov=telek --cov-report=term -v        # tests + coverage
uv run black --check telek tests                              # formatting
uv run isort --check-only telek tests                         # import order
uv run flake8 telek tests                                     # lint
uv run bandit -c pyproject.toml -r telek                      # security
markdownlint-cli2 "**/*.md" "#node_modules"                   # markdown lint
uv run telek --version                                        # smoke test
python .claude/skills/version-bump/scripts/bump.py patch      # bump version
```

Publishing is automated: TestPyPI on PRs (non-fork), PyPI on push to
`main`, both via OIDC Trusted Publishing — no API tokens in CI secrets.

## Conventions in use

- **Python ≥3.12**, hatchling backend, **zero runtime deps** in
  `pyproject.toml` (Telegram libs added in a later PR alongside the
  domain code).
- **CLI shape** modeled on `afi-cli`: argparse with `_TelekArgumentParser`
  routing errors through `emit_error` so no Python tracebacks leak.
- **Every PR bumps the version** in `pyproject.toml` and prepends a
  CHANGELOG entry — the `version-check` CI job enforces this. No
  exceptions for docs / config / CI-only PRs (AgentCulture rule).
- **`--json` everywhere** that produces a listing or report. Errors in
  JSON mode emit `{code, message, remediation}` to stderr; text mode
  renders `error: ... / hint: ...`.
- **Mutation safety** (load-bearing for telek): every Telegram-side write
  verb (when domain code lands) defaults to dry-run; `--apply` to commit.
- **GitHub signatures.** Posts (PRs, comments, cross-repo issues) sign as
  `- telek (Claude)`. The `cicd` and `communicate` skills auto-apply this
  via `agtag` — don't hand-author the trailing nick.
- **Bot tokens, group IDs, webhook secrets are never committed.** Live in
  repo secrets or git-ignored `.env`.

## Skills convention

Every skill in `.claude/skills/<name>/` has:

- `SKILL.md` with frontmatter `name:` matching the directory name.
- A `scripts/` directory holding all entry-point scripts.
- **No reach-outs**: scripts must not import from other skills, other
  repos, or `~/.claude/...` / `~/.config/...`. Helpers live inside the
  same skill's `scripts/`.

Provenance for each vendored skill is recorded in
[`docs/skill-sources.md`](./docs/skill-sources.md).

## Per-machine config

`.claude/skills.local.yaml.example` documents every key (committed).
Copy it to `.claude/skills.local.yaml` (git-ignored) and edit. Skills
read the local file first, falling back to the example.

## Roadmap

- **v0.2 (next PR):** Telegram surface — `telek bot send`,
  `telek group roster`, `telek group pin`. Brings `python-telegram-bot`
  as the first runtime dependency. Every write verb dry-run by default.
- **v0.3+:** Scheduled announcements, moderation rules,
  `telek explain bot send` catalog entries.
