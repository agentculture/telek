"""Tests for telegram_agent.telegram._plan.ValidatedPlan.to_dict()."""

from __future__ import annotations

from telegram_agent.telegram._plan import (
    PinIntent,
    RosterIntent,
    SendIntent,
    ValidatedPlan,
)


def _bot_self() -> dict:
    return {
        "user_id": 42,
        "status": "administrator",
        "permissions": {"can_post": True, "can_pin": True},
    }


def _chat() -> dict:
    return {"id": -1001, "type": "supergroup", "title": "Test", "username": None}


def test_send_plan_to_dict_includes_text_preview():
    plan = ValidatedPlan(
        verb="bot.send",
        chat=_chat(),
        bot_self=_bot_self(),
        intent=SendIntent(
            text_preview="hello world",
            parse_mode="none",
            silent=False,
            reply_to=None,
        ),
        dry_run=True,
    )
    d = plan.to_dict()
    assert d["verb"] == "bot.send"
    assert d["dry_run"] is True
    assert d["intent"]["text_preview"] == "hello world"
    assert d["intent"]["parse_mode"] == "none"
    assert d["bot_self"]["user_id"] == 42


def test_send_plan_truncates_long_preview():
    long = "x" * 200
    intent = SendIntent(text_preview=long, parse_mode="none", silent=False, reply_to=None)
    truncated = intent.to_dict()["text_preview"]
    assert len(truncated) <= 81
    assert truncated.endswith("…")


def test_pin_plan_to_dict_includes_action_and_message():
    plan = ValidatedPlan(
        verb="group.pin",
        chat=_chat(),
        bot_self=_bot_self(),
        intent=PinIntent(action="pin", message_id=123, silent=True),
        dry_run=False,
    )
    d = plan.to_dict()
    assert d["verb"] == "group.pin"
    assert d["intent"]["action"] == "pin"
    assert d["intent"]["message_id"] == 123
    assert d["intent"]["silent"] is True
    assert d["dry_run"] is False


def test_pin_plan_unpin_with_no_message_id_serializes_none():
    plan = ValidatedPlan(
        verb="group.pin",
        chat=_chat(),
        bot_self=_bot_self(),
        intent=PinIntent(action="unpin", message_id=None, silent=False),
        dry_run=True,
    )
    d = plan.to_dict()
    assert d["intent"]["message_id"] is None
    assert d["intent"]["action"] == "unpin"


def test_roster_plan_to_dict_includes_member_count_and_admins():
    plan = ValidatedPlan(
        verb="group.roster",
        chat=_chat(),
        bot_self=_bot_self(),
        intent=RosterIntent(
            member_count=17,
            administrators=[
                {
                    "user_id": 1,
                    "username": "alice",
                    "first_name": "Alice",
                    "status": "creator",
                    "can_post": None,
                    "can_pin": None,
                }
            ],
        ),
        dry_run=False,
    )
    d = plan.to_dict()
    assert d["verb"] == "group.roster"
    assert d["intent"]["member_count"] == 17
    assert d["intent"]["administrators"][0]["username"] == "alice"
    assert d["intent"]["limits"]["note"].lower().startswith("bot api")


def test_plan_warnings_default_empty_list():
    plan = ValidatedPlan(
        verb="bot.send",
        chat=_chat(),
        bot_self=_bot_self(),
        intent=SendIntent(text_preview="x", parse_mode="none", silent=False, reply_to=None),
        dry_run=True,
    )
    assert plan.to_dict()["warnings"] == []
