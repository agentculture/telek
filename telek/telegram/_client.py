"""Sync façade over python-telegram-bot.

CLI verbs stay synchronous (matching the existing learn/explain/whoami
pattern) by wrapping each async Bot method with asyncio.run. The lib is
imported lazily inside __init__ so `telek --help` and the non-Telegram
verbs work without the optional dep installed.
"""

from __future__ import annotations

import asyncio
from typing import Any

from telek.cli._errors import EXIT_ENV_ERROR, TelekError


class TelegramClient:
    """Synchronous façade over telegram.Bot."""

    def __init__(self, token: str | None) -> None:
        if not token:
            raise TelekError(
                code=EXIT_ENV_ERROR,
                message="TELEK_BOT_TOKEN not set",
                remediation=(
                    "set TELEK_BOT_TOKEN in your environment or a local .env file "
                    "(get the token from @BotFather)"
                ),
            )
        try:
            from telegram import Bot
        except ImportError as exc:
            raise TelekError(
                code=EXIT_ENV_ERROR,
                message="python-telegram-bot not installed",
                remediation="pip install 'telek[telegram]'",
            ) from exc

        self._token = token
        self._bot = Bot(token=token)

    @staticmethod
    def _run(coro):
        return asyncio.run(coro)

    def get_me(self) -> dict[str, Any]:
        user = self._run(self._bot.get_me())
        return {"user_id": user.id, "username": user.username}

    def get_chat(self, chat: str) -> dict[str, Any]:
        c = self._run(self._bot.get_chat(chat))
        return {
            "id": c.id,
            "type": c.type,
            "title": getattr(c, "title", None),
            "username": getattr(c, "username", None),
        }

    def get_chat_member(self, chat: str, user_id: int) -> dict[str, Any]:
        m = self._run(self._bot.get_chat_member(chat, user_id))
        return _serialize_member(m)

    def get_chat_member_count(self, chat: str) -> int:
        return int(self._run(self._bot.get_chat_member_count(chat)))

    def get_chat_administrators(self, chat: str) -> list[dict[str, Any]]:
        admins = self._run(self._bot.get_chat_administrators(chat))
        return [_serialize_admin(a) for a in admins]

    def send_message(
        self,
        chat: str,
        text: str,
        parse_mode: str,
        silent: bool,
        reply_to: int | None,
    ) -> dict[str, Any]:
        ptb_parse_mode = None if parse_mode == "none" else parse_mode
        kwargs: dict[str, Any] = {
            "chat_id": chat,
            "text": text,
            "parse_mode": ptb_parse_mode,
            "disable_notification": silent,
        }
        if reply_to is not None:
            kwargs["reply_to_message_id"] = reply_to
        msg = self._run(self._bot.send_message(**kwargs))
        return {"message_id": msg.message_id}

    def pin_chat_message(self, chat: str, message_id: int, silent: bool) -> None:
        self._run(
            self._bot.pin_chat_message(
                chat_id=chat,
                message_id=message_id,
                disable_notification=silent,
            )
        )

    def unpin_chat_message(self, chat: str, message_id: int | None) -> None:
        self._run(
            self._bot.unpin_chat_message(chat_id=chat, message_id=message_id)
        )


def _serialize_member(m: Any) -> dict[str, Any]:
    user = m.user
    return {
        "user_id": user.id,
        "username": user.username,
        "first_name": getattr(user, "first_name", None),
        "status": m.status,
        "permissions": _member_permissions(m),
    }


def _serialize_admin(m: Any) -> dict[str, Any]:
    base = _serialize_member(m)
    perms = base["permissions"]
    return {
        "user_id": base["user_id"],
        "username": base["username"],
        "first_name": base["first_name"],
        "status": base["status"],
        "can_post": perms.get("can_post"),
        "can_pin": perms.get("can_pin"),
        "can_invite": perms.get("can_invite"),
    }


def _member_permissions(m: Any) -> dict[str, Any]:
    return {
        "can_post": getattr(m, "can_post_messages", None),
        "can_pin": getattr(m, "can_pin_messages", None),
        "can_invite": getattr(m, "can_invite_users", None),
        "can_send_messages": getattr(m, "can_send_messages", None),
    }
