"""`telegram-agent bot ...` — bot-scoped Telegram verbs."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from telegram_agent.cli._errors import EXIT_ENV_ERROR, EXIT_USER_ERROR, TelegramAgentError
from telegram_agent.cli._output import emit_result
from telegram_agent.telegram import (
    SendIntent,
    TelegramClient,
    ValidatedPlan,
    load_token,
)
from telegram_agent.telegram._errors import wrap as wrap_telegram_error


def _build_client(token: str | None) -> TelegramClient:
    return TelegramClient(token=token)


def _bot_self_dict(me: dict[str, Any], member: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_id": me["user_id"],
        "status": member["status"],
        "permissions": dict(member.get("permissions") or {}),
    }


def _resolve_text(args: argparse.Namespace) -> str:
    if args.text is not None:
        return args.text
    if args.text_stdin:
        return sys.stdin.read()
    raise TelegramAgentError(
        code=EXIT_USER_ERROR,
        message="missing message body",
        remediation="pass --text '...' or --text-stdin",
    )


def _validate_send(
    client: TelegramClient, args: argparse.Namespace, token: str | None
) -> tuple[ValidatedPlan, str]:
    try:
        me = client.get_me()
        chat = client.get_chat(args.chat)
        member = client.get_chat_member(args.chat, me["user_id"])
    except TelegramAgentError:
        raise
    except Exception as exc:
        raise wrap_telegram_error(exc, token=token) from exc

    status = member["status"]
    if status not in ("member", "administrator", "creator"):
        raise TelegramAgentError(
            code=EXIT_USER_ERROR,
            message=f"bot is not in chat (status={status})",
            remediation="add the bot to the chat first",
        )

    perms = member.get("permissions") or {}
    if chat["type"] == "channel" and not perms.get("can_post"):
        raise TelegramAgentError(
            code=EXIT_USER_ERROR,
            message="bot lacks can_post_messages on this channel",
            remediation="promote the bot and grant post permission",
        )
    if perms.get("can_send_messages") is False:
        raise TelegramAgentError(
            code=EXIT_USER_ERROR,
            message="group has messages disabled for non-admins",
            remediation="promote the bot or unlock the group",
        )

    text = _resolve_text(args)
    intent = SendIntent(
        text_preview=text,
        parse_mode=args.parse_mode,
        silent=args.silent,
        reply_to=args.reply_to,
    )
    plan = ValidatedPlan(
        verb="bot.send",
        chat=chat,
        bot_self=_bot_self_dict(me, member),
        intent=intent,
        dry_run=not args.apply,
    )
    return plan, text


def _run_send(args: argparse.Namespace) -> None:
    token = load_token()
    if not token:
        raise TelegramAgentError(
            code=EXIT_ENV_ERROR,
            message="TELEGRAM_AGENT_BOT_TOKEN is not set",
            remediation="set TELEGRAM_AGENT_BOT_TOKEN in env or .env file",
        )
    client = _build_client(token)
    plan, text = _validate_send(client, args, token)

    if not args.apply:
        emit_result(plan.to_dict(), json_mode=args.json)
        return

    try:
        result = client.send_message(
            chat=args.chat,
            text=text,
            parse_mode=args.parse_mode,
            silent=args.silent,
            reply_to=args.reply_to,
        )
    except TelegramAgentError:
        raise
    except Exception as exc:
        raise wrap_telegram_error(exc, token=token) from exc

    out = plan.to_dict()
    out["dry_run"] = False
    out["message_id"] = result["message_id"]
    emit_result(out, json_mode=args.json)


def register(sub: argparse._SubParsersAction) -> None:
    bot = sub.add_parser("bot", help="bot-scoped Telegram verbs")
    bot_sub = bot.add_subparsers(dest="bot_command")
    bot_sub.required = True

    send = bot_sub.add_parser("send", help="send a message to a chat")
    send.add_argument("--chat", required=True, help="chat id or @username")
    send.add_argument("--text", default=None, help="message body")
    send.add_argument(
        "--text-stdin",
        action="store_true",
        help="read message body from stdin",
    )
    send.add_argument(
        "--parse-mode",
        choices=("none", "markdown", "html"),
        default="none",
    )
    send.add_argument("--silent", action="store_true", help="suppress notification on send")
    send.add_argument("--reply-to", type=int, default=None)
    send.add_argument("--apply", action="store_true", help="actually send")
    send.add_argument("--json", action="store_true")
    send.set_defaults(func=_run_send)
