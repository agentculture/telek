"""`telek group ...` — group-scoped Telegram verbs."""

from __future__ import annotations

import argparse
from typing import Any

from telek.cli._errors import EXIT_USER_ERROR, TelekError
from telek.cli._output import emit_result
from telek.telegram import (
    PinIntent,
    RosterIntent,
    TelegramClient,
    ValidatedPlan,
    load_token,
)
from telek.telegram._errors import wrap as wrap_telegram_error


def _build_client(token: str | None) -> TelegramClient:
    return TelegramClient(token=token)


def _bot_self_dict(me: dict[str, Any], member: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_id": me["user_id"],
        "status": member["status"],
        "permissions": dict(member.get("permissions", {})),
    }


def _shared_probes(
    client: TelegramClient, chat_arg: str, token: str | None
) -> tuple[dict, dict, dict]:
    try:
        me = client.get_me()
        chat = client.get_chat(chat_arg)
        member = client.get_chat_member(chat_arg, me["user_id"])
    except TelekError:
        raise
    except Exception as exc:
        raise wrap_telegram_error(exc, token=token) from exc
    return me, chat, member


# roster

def _run_roster(args: argparse.Namespace) -> int:
    token = load_token()
    client = _build_client(token)
    me, chat, member = _shared_probes(client, args.chat, token)

    try:
        count = client.get_chat_member_count(args.chat)
        admins = client.get_chat_administrators(args.chat)
    except TelekError:
        raise
    except Exception as exc:
        raise wrap_telegram_error(exc, token=token) from exc

    plan = ValidatedPlan(
        verb="group.roster",
        chat=chat,
        bot_self=_bot_self_dict(me, member),
        intent=RosterIntent(member_count=count, administrators=admins),
        dry_run=False,
    )
    emit_result(plan.to_dict(), json_mode=args.json)
    return 0


# pin

def _validate_pin(
    args: argparse.Namespace,
    me: dict[str, Any],
    chat: dict[str, Any],
    member: dict[str, Any],
) -> ValidatedPlan:
    action = "unpin" if args.unpin else "pin"
    message_id = args.message

    if action == "pin" and message_id is None:
        raise TelekError(
            code=EXIT_USER_ERROR,
            message="--message is required when pinning",
            remediation="pass --message <id> of the message to pin",
        )

    perms = member.get("permissions") or {}
    if member["status"] != "administrator" or not perms.get("can_pin"):
        raise TelekError(
            code=EXIT_USER_ERROR,
            message="bot lacks can_pin_messages",
            remediation="promote the bot to admin with the pin permission",
        )

    intent = PinIntent(action=action, message_id=message_id, silent=args.silent)
    return ValidatedPlan(
        verb="group.pin",
        chat=chat,
        bot_self=_bot_self_dict(me, member),
        intent=intent,
        dry_run=not args.apply,
    )


def _run_pin(args: argparse.Namespace) -> int:
    token = load_token()
    client = _build_client(token)
    me, chat, member = _shared_probes(client, args.chat, token)
    plan = _validate_pin(args, me, chat, member)

    if not args.apply:
        emit_result(plan.to_dict(), json_mode=args.json)
        return 0

    try:
        if args.unpin:
            client.unpin_chat_message(chat=args.chat, message_id=args.message)
        else:
            client.pin_chat_message(
                chat=args.chat, message_id=args.message, silent=args.silent
            )
    except TelekError:
        raise
    except Exception as exc:
        raise wrap_telegram_error(exc, token=token) from exc

    out = plan.to_dict()
    out["dry_run"] = False
    emit_result(out, json_mode=args.json)
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    group = sub.add_parser("group", help="group-scoped Telegram verbs")
    group_sub = group.add_subparsers(dest="group_command")
    group_sub.required = True

    roster = group_sub.add_parser("roster", help="list count + admins + bot self")
    roster.add_argument("--chat", required=True)
    roster.add_argument("--json", action="store_true")
    roster.set_defaults(func=_run_roster)

    pin = group_sub.add_parser("pin", help="pin or unpin a message")
    pin.add_argument("--chat", required=True)
    pin.add_argument("--message", type=int, default=None)
    pin.add_argument("--silent", action="store_true", help="suppress notification on pin")
    pin.add_argument("--unpin", action="store_true")
    pin.add_argument("--apply", action="store_true")
    pin.add_argument("--json", action="store_true")
    pin.set_defaults(func=_run_pin)
