"""Tests for telegram_agent.telegram._errors.wrap()."""

from __future__ import annotations

import pytest

from telegram_agent.cli._errors import EXIT_ENV_ERROR, EXIT_USER_ERROR
from telegram_agent.telegram._errors import wrap

telegram = pytest.importorskip("telegram")
from telegram.error import (  # noqa: E402
    BadRequest,
    Forbidden,
    InvalidToken,
    NetworkError,
    RetryAfter,
    TelegramError,
    TimedOut,
)


def test_invalid_token_maps_to_env_error():
    err = wrap(InvalidToken("Invalid token"), token=None)
    assert err.code == EXIT_ENV_ERROR
    assert "rejected" in err.message.lower() or "token" in err.message.lower()
    assert "BotFather" in err.remediation


def test_bad_request_chat_not_found_is_user_error():
    err = wrap(BadRequest("Chat not found"), token=None)
    assert err.code == EXIT_USER_ERROR
    assert "chat not found" in err.message.lower()
    assert "member" in err.remediation.lower()


def test_bad_request_no_rights_is_user_error():
    err = wrap(BadRequest("not enough rights to send messages"), token=None)
    assert err.code == EXIT_USER_ERROR
    assert "permission" in err.message.lower() or "rights" in err.message.lower()
    assert "promote" in err.remediation.lower()


def test_forbidden_bot_kicked_is_user_error():
    err = wrap(Forbidden("Forbidden: bot was kicked from the group chat"), token=None)
    assert err.code == EXIT_USER_ERROR
    assert "not in this chat" in err.message.lower()


def test_retry_after_is_env_error_with_seconds():
    exc = RetryAfter(retry_after=12)
    err = wrap(exc, token=None)
    assert err.code == EXIT_ENV_ERROR
    assert "12" in err.message
    assert "auto-retry" in err.remediation.lower() or "wait" in err.remediation.lower()


def test_network_error_is_env_error():
    err = wrap(NetworkError("connection reset"), token=None)
    assert err.code == EXIT_ENV_ERROR
    assert "network" in err.message.lower()


def test_timed_out_is_env_error():
    err = wrap(TimedOut(), token=None)
    assert err.code == EXIT_ENV_ERROR
    assert "network" in err.message.lower()


def test_other_bad_request_passes_through_as_user_error():
    err = wrap(BadRequest("Some unexpected detail"), token=None)
    assert err.code == EXIT_USER_ERROR
    assert "Some unexpected detail" in err.message


def test_other_telegram_error_is_env_error():
    err = wrap(TelegramError("Unknown server problem"), token=None)
    assert err.code == EXIT_ENV_ERROR
    assert "Unknown server problem" in err.message


def test_wrap_redacts_token_in_message():
    err = wrap(BadRequest("oops with abc123 leaked"), token="abc123")
    assert "abc123" not in err.message
    assert "***" in err.message


def test_wrap_passes_unknown_exception_through():
    err = wrap(RuntimeError("not a telegram error"), token=None)
    assert err.code == EXIT_ENV_ERROR
    assert "not a telegram error" in err.message
