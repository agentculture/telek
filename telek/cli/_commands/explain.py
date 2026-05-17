"""``telek explain <path>...`` — markdown catalog lookup.

Resolves zero or more path tokens to a short markdown body. Unknown paths
raise :class:`TelekError` with a remediation pointing at ``telek explain``.

Today's catalog covers only the universal verbs (``learn``, ``explain``,
``whoami``) — domain verbs (``bot``, ``group``) will be added when their
implementations land.
"""

from __future__ import annotations

import argparse

from telek.cli._errors import EXIT_USER_ERROR, TelekError
from telek.cli._output import emit_result

_ROOT = """\
# telek

Agent-first Telegram community management tools. Today the CLI exposes the
universal agent-affordance verbs only; the Telegram surface (`bot`,
`group`) is intentionally absent and lands in a follow-up PR.

## Universal verbs

- `telek learn` — self-teaching prompt (text or `--json`).
- `telek explain <path>` — markdown docs for any verb path.
- `telek whoami` — agent identity + Telegram config status probe.

## Conventions

- Every command that produces a listing or report honours `--json`.
- Errors carry a `{code, message, remediation}` shape; text mode renders as
  `error: ...` + `hint: ...` on stderr.
- Exit codes: `0` success, `1` user-input error, `2` environment error.
- Write verbs (when added) will default to dry-run; `--apply` to commit.

See `telek explain learn`, `telek explain explain`, `telek explain whoami`
for per-verb detail.
"""

_LEARN = """\
# telek learn

Prints a structured self-teaching prompt describing telek's purpose, verb
map, exit-code policy, and `--json` support. The output is stable enough
that an agent can read it and author its own usage skill without parsing
`--help`.

## Flags

- `--json` — emit a structured payload instead of prose. Keys include
  `tool`, `version`, `purpose`, `commands`, `exit_codes`, `env`,
  `mutation_safety`.
"""

_EXPLAIN = """\
# telek explain

Resolves a noun/verb path to markdown. With no arguments, prints the
top-level overview. With one or more tokens (`telek explain whoami`,
`telek explain bot send` once domain verbs land), prints the per-verb body.

## Flags

- `--json` — wrap the markdown in `{"path": [...], "markdown": "..."}`.

## Errors

Unknown paths exit `1` with `error: unknown path: <tokens>` and a hint
pointing back at `telek explain`.
"""

_WHOAMI = """\
# telek whoami

The smallest auth probe. Reports:

- `nick` — agent suffix from `culture.yaml` (falls back to `telek`).
- `version` — `telek.__version__`.
- `bot_token_configured` — boolean: is `TELEK_BOT_TOKEN` set in the
  environment? The token itself is **never** printed or logged.

Use this to verify (without contacting Telegram) that the environment is
provisioned for write verbs. Always exits `0`; non-configured state is a
field on the report, not an error.

## Flags

- `--json` — structured payload.
"""

_CATALOG: dict[tuple[str, ...], str] = {
    (): _ROOT,
    ("telek",): _ROOT,
    ("learn",): _LEARN,
    ("explain",): _EXPLAIN,
    ("whoami",): _WHOAMI,
}


def resolve(path: tuple[str, ...]) -> str:
    body = _CATALOG.get(path)
    if body is None:
        raise TelekError(
            code=EXIT_USER_ERROR,
            message=f"unknown path: {' '.join(path) or '(empty)'}",
            remediation="run 'telek explain' for the top-level map",
        )
    return body


def cmd_explain(args: argparse.Namespace) -> int:
    path = tuple(args.path) if args.path else ()
    markdown = resolve(path)
    json_mode = bool(getattr(args, "json", False))
    if json_mode:
        emit_result({"path": list(path), "markdown": markdown}, json_mode=True)
    else:
        emit_result(markdown, json_mode=False)
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "explain",
        help="Print markdown docs for a noun/verb path (e.g. 'telek explain whoami').",
    )
    p.add_argument(
        "path",
        nargs="*",
        help="Command path tokens; empty = root (same as 'telek').",
    )
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_explain)
