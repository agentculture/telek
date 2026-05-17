"""``telek whoami`` — smallest auth probe.

Reports the agent's identity (from `culture.yaml`), package version, and
whether the Telegram bot token is configured in the environment. Does NOT
call Telegram and NEVER prints the token itself.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from telek import __version__
from telek.cli._output import emit_result

_BOT_TOKEN_ENV = "TELEK_BOT_TOKEN"  # nosec B105 - env var name, not a credential
_FALLBACK_NICK = "telek"


def _read_nick() -> str:
    """Return the first agent suffix from `culture.yaml`, or the fallback.

    Parsed without a YAML dependency to keep telek's runtime deps empty.
    Looks for the first ``suffix: <value>`` line under ``agents:``; anything
    fancier than the documented two-line shape falls back to ``telek``.
    """
    cfg = Path("culture.yaml")
    if not cfg.is_file():
        return _FALLBACK_NICK
    try:
        text = cfg.read_text(encoding="utf-8")
    except OSError:
        return _FALLBACK_NICK
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("suffix:"):
            _, _, value = stripped.partition(":")
            value = value.strip().strip("'\"")
            if value:
                return value
    return _FALLBACK_NICK


def _report() -> dict[str, object]:
    return {
        "nick": _read_nick(),
        "version": __version__,
        "bot_token_configured": bool(os.environ.get(_BOT_TOKEN_ENV)),
    }


def cmd_whoami(args: argparse.Namespace) -> None:
    report = _report()
    json_mode = bool(getattr(args, "json", False))
    if json_mode:
        emit_result(report, json_mode=True)
        return
    text = (
        f"nick: {report['nick']}\n"
        f"version: {report['version']}\n"
        f"bot_token_configured: {str(report['bot_token_configured']).lower()}\n"
        f"  ({_BOT_TOKEN_ENV} is{'' if report['bot_token_configured'] else ' not'} set)"
    )
    emit_result(text, json_mode=False)


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "whoami",
        help="Report agent nick, version, and whether TELEK_BOT_TOKEN is set.",
    )
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_whoami)
