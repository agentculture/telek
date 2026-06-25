"""Tests for telegram_agent.telegram._client.TelegramClient (lazy import + façade)."""

from __future__ import annotations

import pytest

from telegram_agent.cli._errors import EXIT_ENV_ERROR, TelegramAgentError


def test_client_requires_token():
    from telegram_agent.telegram._client import TelegramClient

    with pytest.raises(TelegramAgentError) as exc:
        TelegramClient(token=None)
    assert exc.value.code == EXIT_ENV_ERROR
    assert "TELEGRAM_AGENT_BOT_TOKEN" in exc.value.message


def test_client_missing_library_raises_clean(monkeypatch):
    """If python-telegram-bot can't import, TelegramClient raises TelegramAgentError."""
    import sys

    from telegram_agent.telegram._client import TelegramClient

    monkeypatch.setitem(sys.modules, "telegram", None)

    with pytest.raises(TelegramAgentError) as exc:
        TelegramClient(token="fake")
    assert exc.value.code == EXIT_ENV_ERROR
    assert "python-telegram-bot" in exc.value.message
    assert "telegram-agent[telegram]" in exc.value.remediation
