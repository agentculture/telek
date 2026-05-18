"""Map python-telegram-bot exceptions to TelekError.

This module is the only place telegram.error exceptions cross into the rest
of telek. Every wrapped message is run through telek.telegram._config.redact
so a token accidentally embedded in an upstream string never escapes.
"""

from __future__ import annotations

from telek.cli._errors import EXIT_ENV_ERROR, EXIT_USER_ERROR, TelekError
from telek.telegram._config import redact


def _wrap_forbidden(msg: str) -> TelekError:
    lowered = msg.lower()
    if "kicked" in lowered or "not a member" in lowered or "blocked" in lowered:
        return TelekError(
            code=EXIT_USER_ERROR,
            message="bot is not in this chat",
            remediation="add the bot to the chat first",
        )
    return TelekError(
        code=EXIT_USER_ERROR,
        message=f"forbidden: {msg}",
        remediation="check the bot has access to this chat",
    )


def _wrap_bad_request(msg: str) -> TelekError:
    lowered = msg.lower()
    if "chat not found" in lowered:
        return TelekError(
            code=EXIT_USER_ERROR,
            message=f"chat not found: {msg}",
            remediation="verify id/username; ensure the bot is a member",
        )
    if "not enough rights" in lowered or "have no rights" in lowered:
        return TelekError(
            code=EXIT_USER_ERROR,
            message=f"bot lacks required permission: {msg}",
            remediation="promote the bot and grant the needed permission",
        )
    return TelekError(
        code=EXIT_USER_ERROR,
        message=msg,
        remediation="see telegram API docs for details",
    )


def wrap(exc: BaseException, *, token: str | None) -> TelekError:
    """Convert a python-telegram-bot exception into a TelekError."""
    from telegram.error import (
        BadRequest,
        Forbidden,
        InvalidToken,
        NetworkError,
        RetryAfter,
        TelegramError,
        TimedOut,
    )

    raw_msg = str(getattr(exc, "message", "") or str(exc))
    msg = redact(raw_msg, token)

    if isinstance(exc, InvalidToken):
        return TelekError(
            code=EXIT_ENV_ERROR,
            message="telegram rejected bot token",
            remediation="check TELEK_BOT_TOKEN with @BotFather",
        )

    if isinstance(exc, RetryAfter):
        seconds = getattr(exc, "retry_after", "?")
        return TelekError(
            code=EXIT_ENV_ERROR,
            message=f"rate limited; retry after {seconds}s",
            remediation="wait and retry; v0.2 does not auto-retry",
        )

    if isinstance(exc, Forbidden):
        return _wrap_forbidden(msg)

    # BadRequest inherits from NetworkError in python-telegram-bot v21;
    # this branch MUST appear before the NetworkError arm below.
    if isinstance(exc, BadRequest):
        return _wrap_bad_request(msg)

    if isinstance(exc, (NetworkError, TimedOut)):
        return TelekError(
            code=EXIT_ENV_ERROR,
            message=f"network error talking to telegram: {msg}",
            remediation="check connectivity and retry",
        )

    if isinstance(exc, TelegramError):
        return TelekError(
            code=EXIT_ENV_ERROR,
            message=msg,
            remediation="",
        )

    return TelekError(
        code=EXIT_ENV_ERROR,
        message=msg or exc.__class__.__name__,
        remediation="",
    )
