"""Sync façade over python-telegram-bot.

CLI verbs stay synchronous (matching the existing learn/explain/whoami
pattern) by wrapping each async Bot method with asyncio.run. The lib is
imported lazily inside __init__ so `telek --help` and the non-Telegram
verbs work without the optional dep installed.

Each public method creates a fresh Bot instance via `async with
bot_class(token=...) as bot` inside a single asyncio.run call.
python-telegram-bot v21's Bot holds an httpx connection pool that is
tied to the event loop in which it was first awaited; asyncio.run closes
that loop on exit, so reusing one Bot across multiple asyncio.run calls
raises RuntimeError('Event loop is closed') on the second call. Building
the Bot per-call ensures httpx initialises and tears down within the
same loop.
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
        self._bot_class = Bot

    def _run(self, coro_fn):
        """Run an async callable that takes a fresh Bot.

        coro_fn must be ``async def fn(bot) -> result``.
        A new Bot is created via ``async with`` for each call so its httpx
        connection pool is initialised and torn down inside a single
        asyncio.run event loop, avoiding RuntimeError('Event loop is closed')
        on the second call.
        """

        async def _wrapped():
            async with self._bot_class(token=self._token) as bot:
                return await coro_fn(bot)

        return asyncio.run(_wrapped())

    def get_me(self) -> dict[str, Any]:
        async def _fn(bot):
            return await bot.get_me()

        user = self._run(_fn)
        return {"user_id": user.id, "username": user.username}

    def get_chat(self, chat: str) -> dict[str, Any]:
        async def _fn(bot):
            return await bot.get_chat(chat)

        c = self._run(_fn)
        return {
            "id": c.id,
            "type": c.type,
            "title": getattr(c, "title", None),
            "username": getattr(c, "username", None),
        }

    def get_chat_member(self, chat: str, user_id: int) -> dict[str, Any]:
        async def _fn(bot):
            return await bot.get_chat_member(chat, user_id)

        m = self._run(_fn)
        return _serialize_member(m)

    def get_chat_member_count(self, chat: str) -> int:
        async def _fn(bot):
            return await bot.get_chat_member_count(chat)

        return int(self._run(_fn))

    def get_chat_administrators(self, chat: str) -> list[dict[str, Any]]:
        async def _fn(bot):
            return await bot.get_chat_administrators(chat)

        admins = self._run(_fn)
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

        async def _fn(bot):
            kwargs: dict[str, Any] = {
                "chat_id": chat,
                "text": text,
                "parse_mode": ptb_parse_mode,
                "disable_notification": silent,
            }
            if reply_to is not None:
                kwargs["reply_to_message_id"] = reply_to
            return await bot.send_message(**kwargs)

        msg = self._run(_fn)
        return {"message_id": msg.message_id}

    def pin_chat_message(self, chat: str, message_id: int, silent: bool) -> None:
        async def _fn(bot):
            return await bot.pin_chat_message(
                chat_id=chat,
                message_id=message_id,
                disable_notification=silent,
            )

        self._run(_fn)

    def unpin_chat_message(self, chat: str, message_id: int | None) -> None:
        async def _fn(bot):
            return await bot.unpin_chat_message(chat_id=chat, message_id=message_id)

        self._run(_fn)


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
