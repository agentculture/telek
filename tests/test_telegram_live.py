"""Live smoke tests against the real Telegram Bot API.

Skipped automatically when the gating env vars are absent (so CI is
unaffected). Run manually with the chat IDs of a private chat the bot
can DM and a group/supergroup the bot is a member (and admin) of:

    export TELEK_BOT_TOKEN=...
    export TELEK_LIVE_TEST_USER_CHAT=6558999365         # numeric user chat_id
    export TELEK_LIVE_TEST_GROUP_CHAT=-1003852081102    # numeric group chat_id
    uv run pytest tests/test_telegram_live.py -v

These tests send real messages and pin/unpin in the target group.
"""

from __future__ import annotations

import json
import os

import pytest

from telek.cli import main
from telek.telegram._config import load_token

pytestmark = pytest.mark.live


def _need_env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        pytest.skip(f"set {name} to enable live tests")
    return val


@pytest.fixture(scope="module")
def user_chat() -> str:
    return _need_env("TELEK_LIVE_TEST_USER_CHAT")


@pytest.fixture(scope="module")
def group_chat() -> str:
    return _need_env("TELEK_LIVE_TEST_GROUP_CHAT")


@pytest.fixture(scope="module", autouse=True)
def _ensure_token():
    if not load_token():
        pytest.skip("TELEK_BOT_TOKEN not set (env or .env)")


def _last_json(capsys) -> dict:
    out = capsys.readouterr().out.strip()
    return json.loads(out.splitlines()[-1])


def test_bot_send_dry_run_to_user(user_chat, capsys):
    rc = main(["bot", "send", "--chat", user_chat, "--text", "telek live: dry-run probe", "--json"])
    assert (rc or 0) == 0
    payload = _last_json(capsys)
    assert payload["verb"] == "bot.send"
    assert payload["dry_run"] is True
    assert payload["chat"]["type"] == "private"


def test_bot_send_apply_to_user(user_chat, capsys):
    rc = main(
        ["bot", "send", "--chat", user_chat, "--text", "telek live smoke (DM)", "--apply", "--json"]
    )
    assert (rc or 0) == 0
    payload = _last_json(capsys)
    assert payload["dry_run"] is False
    assert payload["message_id"] > 0


def test_group_roster_returns_admins(group_chat, capsys):
    rc = main(["group", "roster", "--chat", group_chat, "--json"])
    assert (rc or 0) == 0
    payload = _last_json(capsys)
    assert payload["verb"] == "group.roster"
    assert payload["chat"]["type"] in ("group", "supergroup")
    assert payload["intent"]["member_count"] > 0
    assert "Bot API" in payload["intent"]["limits"]["note"]
    assert any(
        a["user_id"] == payload["bot_self"]["user_id"] for a in payload["intent"]["administrators"]
    ), "bot should appear in its own admin list"


def test_group_send_pin_unpin_cycle(group_chat, capsys):
    rc = main(
        [
            "bot",
            "send",
            "--chat",
            group_chat,
            "--text",
            "telek live smoke (will be pinned then unpinned)",
            "--apply",
            "--json",
        ]
    )
    assert (rc or 0) == 0
    sent = _last_json(capsys)
    msg_id = sent["message_id"]
    assert msg_id > 0

    rc = main(
        [
            "group",
            "pin",
            "--chat",
            group_chat,
            "--message",
            str(msg_id),
            "--apply",
            "--json",
        ]
    )
    assert (rc or 0) == 0
    pinned = _last_json(capsys)
    assert pinned["verb"] == "group.pin"
    assert pinned["intent"]["action"] == "pin"
    assert pinned["intent"]["message_id"] == msg_id
    assert pinned["dry_run"] is False

    rc = main(
        [
            "group",
            "pin",
            "--chat",
            group_chat,
            "--message",
            str(msg_id),
            "--unpin",
            "--apply",
            "--json",
        ]
    )
    assert (rc or 0) == 0
    unpinned = _last_json(capsys)
    assert unpinned["intent"]["action"] == "unpin"
    assert unpinned["dry_run"] is False
