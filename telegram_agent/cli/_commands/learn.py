"""``telegram-agent learn`` — the learnability affordance.

Prints a structured self-teaching prompt so an agent can author its own
usage skill without scraping ``--help``. Supports ``--json``.
"""

from __future__ import annotations

import argparse

from telegram_agent import __version__
from telegram_agent.cli._output import emit_result

_TEXT = """\
telegram-agent — agent-first Telegram community management tools.

Purpose
-------
Provide an agent-first surface (CLI today; MCP/HTTP later) for moderating
and operating Telegram communities — group rosters, message moderation,
pinned-post hygiene, scheduled announcements. The Telegram surface (`bot`,
`group`) is live; scheduled announcements and moderation rules are planned.

Universal verbs (agent-first)
-----------------------------
  telegram-agent learn              Print this self-teaching prompt. Supports --json.
  telegram-agent explain <path>...  Print docs for a noun/verb path. Supports --json.
  telegram-agent whoami             Report agent identity + Telegram config status.
                           Supports --json.

Domain verbs (Telegram surface)
-------------------------------
  telegram-agent bot send      Send a message to a chat. Dry-run; --apply to send.
  telegram-agent group roster  List member count, admins, and the bot itself.
  telegram-agent group pin     Pin or unpin a message. Dry-run; --apply to commit.

**Mutation safety:** every write verb defaults to dry-run; pass `--apply`
to actually send a message, pin a post, etc. This is load-bearing — agents
call CLIs in loops, so safe-by-default is the contract, not an option.

Machine-readable output
-----------------------
Every command that produces a listing or report supports --json. Errors in
JSON mode emit {"code", "message", "remediation"} to stderr. Stdout and
stderr are never mixed.

Exit-code policy
----------------
  0 success
  1 user-input error (bad flag, bad path, missing arg)
  2 environment / setup error (TELEGRAM_AGENT_BOT_TOKEN missing, unreadable file)
  3+ reserved

Environment
-----------
  TELEGRAM_AGENT_BOT_TOKEN   Telegram bot token. Required for write verbs once they
                    land. Never logged, never echoed.

More detail
-----------
  telegram-agent explain telegram-agent
  telegram-agent explain learn
  telegram-agent explain whoami

Homepage: https://github.com/agentculture/telegram-agent
"""


def _as_json_payload() -> dict[str, object]:
    return {
        "tool": "telegram-agent",
        "version": __version__,
        "purpose": (
            "Agent-first Telegram community management — moderation, roster, "
            "pinned-post hygiene, scheduled announcements."
        ),
        "commands": [
            {"path": ["learn"], "summary": "Self-teaching prompt."},
            {"path": ["explain"], "summary": "Docs by noun/verb path."},
            {
                "path": ["whoami"],
                "summary": "Report agent nick, version, Telegram config status.",
            },
            {"path": ["bot", "send"], "summary": "Send a message (dry-run; --apply)."},
            {"path": ["group", "roster"], "summary": "Member count, admins, bot self."},
            {"path": ["group", "pin"], "summary": "Pin/unpin a message (dry-run; --apply)."},
        ],
        "exit_codes": {
            "0": "success",
            "1": "user-input error",
            "2": "environment/setup error",
        },
        "json_support": True,
        "explain_pointer": "telegram-agent explain <path> (e.g. 'telegram-agent explain whoami')",
        "env": {
            "TELEGRAM_AGENT_BOT_TOKEN": (  # nosec B105 - env var name, not a credential
                "Telegram bot token. Required once write verbs land. Never logged."
            ),
        },
        "mutation_safety": ("Every write verb defaults to dry-run; pass --apply to commit."),
    }


def cmd_learn(args: argparse.Namespace) -> int:
    json_mode = bool(getattr(args, "json", False))
    if json_mode:
        emit_result(_as_json_payload(), json_mode=True)
    else:
        emit_result(_TEXT, json_mode=False)
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "learn",
        help="Print a structured self-teaching prompt for agent consumers.",
    )
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_learn)
