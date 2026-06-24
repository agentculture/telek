"""Unified CLI entry point for telegram-agent.

Top-level agent-affordance verbs (``learn``, ``explain``, ``whoami``) live
under :mod:`telegram_agent.cli._commands`. Per-noun groups for the Telegram surface
(``bot``, ``group``, ...) will register the same way when domain code lands.

Error propagation contract
--------------------------
Every handler raises :class:`telegram_agent.cli._errors.TelegramAgentError` on failure;
``main()`` catches it via :func:`_dispatch` and routes through
:mod:`telegram_agent.cli._output`. Unknown exceptions are wrapped so no Python
traceback leaks. Argparse errors (unknown verb, missing required arg) route
through the same path via :class:`_TelegramAgentArgumentParser`.
"""

from __future__ import annotations

import argparse
import sys

from telegram_agent import __version__
from telegram_agent.cli._errors import EXIT_USER_ERROR, TelegramAgentError
from telegram_agent.cli._output import emit_error


class _TelegramAgentArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that routes errors through :func:`emit_error`.

    JSON-mode awareness: parse-time errors fire before ``args.json`` exists,
    so :func:`main` pre-scans argv for ``--json`` and sets the class-level
    ``_json_hint``. Shared across subparsers (argparse's subparser factory
    produces instances of the class but doesn't thread state).
    """

    _json_hint: bool = False

    def error(self, message: str) -> None:  # type: ignore[override]
        err = TelegramAgentError(
            code=EXIT_USER_ERROR,
            message=message,
            remediation=f"run '{self.prog} --help' to see valid arguments",
        )
        emit_error(err, json_mode=type(self)._json_hint)
        raise SystemExit(err.code)


def _argv_has_json(argv: list[str] | None) -> bool:
    tokens = argv if argv is not None else sys.argv[1:]
    return any(t == "--json" or t.startswith("--json=") for t in tokens)


def _build_parser() -> argparse.ArgumentParser:
    from telegram_agent.cli._commands import bot as _bot_cmd
    from telegram_agent.cli._commands import explain as _explain_cmd
    from telegram_agent.cli._commands import group as _group_cmd
    from telegram_agent.cli._commands import learn as _learn_cmd
    from telegram_agent.cli._commands import whoami as _whoami_cmd

    parser = _TelegramAgentArgumentParser(
        prog="telegram-agent",
        description="telegram-agent — agent-first Telegram community management tools",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command", parser_class=_TelegramAgentArgumentParser)

    _learn_cmd.register(sub)
    _explain_cmd.register(sub)
    _whoami_cmd.register(sub)
    _bot_cmd.register(sub)
    _group_cmd.register(sub)

    return parser


def _dispatch(args: argparse.Namespace) -> int:
    json_mode = bool(getattr(args, "json", False))
    try:
        rc = args.func(args)
    except TelegramAgentError as err:
        emit_error(err, json_mode=json_mode)
        return err.code
    except Exception as err:  # noqa: BLE001 - last-resort; wrap and route cleanly
        wrapped = TelegramAgentError(
            code=EXIT_USER_ERROR,
            message=f"unexpected: {err.__class__.__name__}: {err}",
            remediation="file a bug at https://github.com/agentculture/telegram-agent/issues",
        )
        emit_error(wrapped, json_mode=json_mode)
        return wrapped.code
    return rc if rc is not None else 0


def main(argv: list[str] | None = None) -> int:
    _TelegramAgentArgumentParser._json_hint = _argv_has_json(argv)
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    return _dispatch(args)


if __name__ == "__main__":
    sys.exit(main())
