"""Tests for telek.telegram._client.TelegramClient (lazy import + façade)."""

from __future__ import annotations

import pytest

from telek.cli._errors import EXIT_ENV_ERROR, TelekError


def test_client_requires_token():
    from telek.telegram._client import TelegramClient

    with pytest.raises(TelekError) as exc:
        TelegramClient(token=None)
    assert exc.value.code == EXIT_ENV_ERROR
    assert "TELEK_BOT_TOKEN" in exc.value.message


def test_client_missing_library_raises_clean(monkeypatch):
    """If python-telegram-bot can't import, TelegramClient raises TelekError."""
    import importlib
    import sys

    from telek.telegram import _client as client_mod

    monkeypatch.setitem(sys.modules, "telegram", None)
    importlib.reload(client_mod)

    with pytest.raises(TelekError) as exc:
        client_mod.TelegramClient(token="fake")
    assert exc.value.code == EXIT_ENV_ERROR
    assert "python-telegram-bot" in exc.value.message
    assert "telek[telegram]" in exc.value.remediation
