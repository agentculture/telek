"""CLI smoke tests for telek bot/group verbs."""

from __future__ import annotations

import json
from typing import Any

import pytest

from telek.cli import main
from telek.cli._errors import EXIT_ENV_ERROR, EXIT_USER_ERROR
from tests.fakes import FakeTelegramClient

pytest.importorskip("telegram")
from telegram.error import BadRequest  # noqa: E402


@pytest.fixture
def fake(monkeypatch) -> FakeTelegramClient:
    client = FakeTelegramClient()
    monkeypatch.setenv("TELEK_BOT_TOKEN", "fake-token")
    monkeypatch.setattr(
        "telek.cli._commands.bot._build_client",
        lambda token: client,
    )
    return client


def _json_of(capsys) -> dict[str, Any]:
    out = capsys.readouterr().out
    return json.loads(out)


# bot send

def test_bot_send_dry_run_default_does_not_send(fake, capsys):
    rc = main(["bot", "send", "--chat", "@test", "--text", "hello", "--json"])
    assert rc == 0
    payload = _json_of(capsys)
    assert payload["verb"] == "bot.send"
    assert payload["dry_run"] is True
    assert payload["intent"]["text_preview"] == "hello"
    assert "send_message" not in [c.method for c in fake.calls]


def test_bot_send_apply_calls_send_message(fake, capsys):
    rc = main(
        ["bot", "send", "--chat", "@test", "--text", "hi", "--apply", "--json"]
    )
    assert rc == 0
    payload = _json_of(capsys)
    assert payload["dry_run"] is False
    sent = [c for c in fake.calls if c.method == "send_message"]
    assert len(sent) == 1
    assert sent[0].kwargs["text"] == "hi"


def test_bot_send_requires_text_or_text_stdin(fake, capsys):
    rc = main(["bot", "send", "--chat", "@test"])
    assert rc == EXIT_USER_ERROR
    err = capsys.readouterr().err
    assert "--text" in err


def test_bot_send_text_stdin_reads_stdin(fake, capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin.read", lambda: "from stdin")
    rc = main(["bot", "send", "--chat", "@test", "--text-stdin", "--apply", "--json"])
    assert rc == 0
    sent = [c for c in fake.calls if c.method == "send_message"]
    assert sent[0].kwargs["text"] == "from stdin"


def test_bot_send_parse_mode_defaults_to_none(fake, capsys):
    rc = main(["bot", "send", "--chat", "@x", "--text", "hi", "--apply", "--json"])
    assert rc == 0
    sent = [c for c in fake.calls if c.method == "send_message"]
    assert sent[0].kwargs["parse_mode"] == "none"


def test_bot_send_missing_token_exits_env_error(monkeypatch, capsys):
    monkeypatch.delenv("TELEK_BOT_TOKEN", raising=False)
    rc = main(["bot", "send", "--chat", "@x", "--text", "hi"])
    assert rc == EXIT_ENV_ERROR


def test_bot_send_chat_not_found_exits_user_error(fake, capsys):
    fake.raise_on["get_chat"] = BadRequest("Chat not found")
    rc = main(["bot", "send", "--chat", "@nope", "--text", "hi"])
    assert rc == EXIT_USER_ERROR


def test_bot_send_silent_flag_threaded_through(fake, capsys):
    rc = main(
        ["bot", "send", "--chat", "@x", "--text", "hi", "--silent", "--apply", "--json"]
    )
    assert rc == 0
    sent = [c for c in fake.calls if c.method == "send_message"]
    assert sent[0].kwargs["silent"] is True


def test_bot_send_reply_to_threaded_through(fake, capsys):
    rc = main(
        ["bot", "send", "--chat", "@x", "--text", "re", "--reply-to", "55",
         "--apply", "--json"]
    )
    assert rc == 0
    sent = [c for c in fake.calls if c.method == "send_message"]
    assert sent[0].kwargs["reply_to"] == 55
