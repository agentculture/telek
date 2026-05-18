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
    monkeypatch.setattr(
        "telek.cli._commands.group._build_client",
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
    rc = main(["bot", "send", "--chat", "@test", "--text", "hi", "--apply", "--json"])
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
    monkeypatch.setattr("telek.cli._commands.bot.load_token", lambda: None)
    rc = main(["bot", "send", "--chat", "@x", "--text", "hi"])
    assert rc == EXIT_ENV_ERROR


def test_bot_send_chat_not_found_exits_user_error(fake, capsys):
    fake.raise_on["get_chat"] = BadRequest("Chat not found")
    rc = main(["bot", "send", "--chat", "@nope", "--text", "hi"])
    assert rc == EXIT_USER_ERROR


def test_bot_send_silent_flag_threaded_through(fake, capsys):
    rc = main(["bot", "send", "--chat", "@x", "--text", "hi", "--silent", "--apply", "--json"])
    assert rc == 0
    sent = [c for c in fake.calls if c.method == "send_message"]
    assert sent[0].kwargs["silent"] is True


def test_bot_send_reply_to_threaded_through(fake, capsys):
    rc = main(
        ["bot", "send", "--chat", "@x", "--text", "re", "--reply-to", "55", "--apply", "--json"]
    )
    assert rc == 0
    sent = [c for c in fake.calls if c.method == "send_message"]
    assert sent[0].kwargs["reply_to"] == 55


# group roster


def test_group_roster_returns_count_admins_botself(fake, capsys):
    fake.member_count = 17
    fake.administrators = [
        {
            "user_id": 1,
            "username": "alice",
            "first_name": "Alice",
            "status": "creator",
            "can_post": None,
            "can_pin": None,
            "can_invite": None,
        }
    ]
    rc = main(["group", "roster", "--chat", "@test", "--json"])
    assert rc == 0
    payload = _json_of(capsys)
    assert payload["verb"] == "group.roster"
    assert payload["intent"]["member_count"] == 17
    assert payload["intent"]["administrators"][0]["username"] == "alice"
    assert "Bot API" in payload["intent"]["limits"]["note"]
    assert payload["bot_self"]["user_id"] == 42


def test_group_roster_no_apply_flag(fake):
    with pytest.raises(SystemExit) as exc:
        main(["group", "roster", "--chat", "@x", "--apply"])
    assert exc.value.code == EXIT_USER_ERROR  # --apply is not defined for roster


# group pin


def test_group_pin_dry_run_default_does_not_pin(fake, capsys):
    rc = main(["group", "pin", "--chat", "@x", "--message", "55", "--json"])
    assert rc == 0
    payload = _json_of(capsys)
    assert payload["verb"] == "group.pin"
    assert payload["intent"]["action"] == "pin"
    assert payload["intent"]["message_id"] == 55
    assert payload["dry_run"] is True
    assert "pin_chat_message" not in [c.method for c in fake.calls]


def test_group_pin_apply_calls_pin(fake, capsys):
    rc = main(["group", "pin", "--chat", "@x", "--message", "55", "--apply", "--json"])
    assert rc == 0
    pinned = [c for c in fake.calls if c.method == "pin_chat_message"]
    assert len(pinned) == 1
    assert pinned[0].kwargs["message_id"] == 55


def test_group_pin_requires_message_when_not_unpin(fake):
    rc = main(["group", "pin", "--chat", "@x"])
    assert rc == EXIT_USER_ERROR


def test_group_pin_unpin_without_message_unpins_current(fake, capsys):
    rc = main(["group", "pin", "--chat", "@x", "--unpin", "--apply", "--json"])
    assert rc == 0
    unpinned = [c for c in fake.calls if c.method == "unpin_chat_message"]
    assert len(unpinned) == 1
    assert unpinned[0].kwargs["message_id"] is None


def test_group_pin_unpin_with_message_unpins_specific(fake, capsys):
    rc = main(["group", "pin", "--chat", "@x", "--unpin", "--message", "55", "--apply", "--json"])
    assert rc == 0
    unpinned = [c for c in fake.calls if c.method == "unpin_chat_message"]
    assert unpinned[0].kwargs["message_id"] == 55


def test_group_pin_blocks_apply_when_bot_lacks_can_pin(fake, capsys):
    fake.bot_member = {
        "user_id": 42,
        "username": "fake_bot",
        "first_name": "Fake",
        "status": "administrator",
        "permissions": {"can_post": True, "can_pin": False},
    }
    rc = main(["group", "pin", "--chat", "@x", "--message", "55", "--apply"])
    assert rc == EXIT_USER_ERROR
    assert "pin_chat_message" not in [c.method for c in fake.calls]
