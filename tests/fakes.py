"""Fake TelegramClient for tests. Records calls; returns canned responses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class _Call:
    method: str
    kwargs: dict[str, Any]


@dataclass
class FakeTelegramClient:
    """In-memory stand-in for telek.telegram.TelegramClient."""

    token: str | None = "fake-token"
    me: dict[str, Any] = field(default_factory=lambda: {"user_id": 42, "username": "fake_bot"})
    chat: dict[str, Any] = field(
        default_factory=lambda: {
            "id": -1001,
            "type": "supergroup",
            "title": "Fake Group",
            "username": None,
        }
    )
    bot_member: dict[str, Any] = field(
        default_factory=lambda: {
            "user_id": 42,
            "username": "fake_bot",
            "first_name": "Fake",
            "status": "administrator",
            "permissions": {
                "can_post": True,
                "can_pin": True,
                "can_send_messages": True,
            },
        }
    )
    member_count: int = 5
    administrators: list[dict[str, Any]] = field(default_factory=list)
    sent_message_id: int = 100
    raise_on: dict[str, BaseException] = field(default_factory=dict)
    calls: list[_Call] = field(default_factory=list)

    def _maybe_raise(self, method: str) -> None:
        exc = self.raise_on.get(method)
        if exc is not None:
            raise exc

    def get_me(self) -> dict[str, Any]:
        self.calls.append(_Call("get_me", {}))
        self._maybe_raise("get_me")
        return dict(self.me)

    def get_chat(self, chat: str) -> dict[str, Any]:
        self.calls.append(_Call("get_chat", {"chat": chat}))
        self._maybe_raise("get_chat")
        return dict(self.chat)

    def get_chat_member(self, chat: str, user_id: int) -> dict[str, Any]:
        self.calls.append(_Call("get_chat_member", {"chat": chat, "user_id": user_id}))
        self._maybe_raise("get_chat_member")
        return dict(self.bot_member)

    def get_chat_member_count(self, chat: str) -> int:
        self.calls.append(_Call("get_chat_member_count", {"chat": chat}))
        self._maybe_raise("get_chat_member_count")
        return self.member_count

    def get_chat_administrators(self, chat: str) -> list[dict[str, Any]]:
        self.calls.append(_Call("get_chat_administrators", {"chat": chat}))
        self._maybe_raise("get_chat_administrators")
        return [dict(a) for a in self.administrators]

    def send_message(
        self,
        chat: str,
        text: str,
        parse_mode: str,
        silent: bool,
        reply_to: int | None,
    ) -> dict[str, Any]:
        self.calls.append(
            _Call(
                "send_message",
                {
                    "chat": chat,
                    "text": text,
                    "parse_mode": parse_mode,
                    "silent": silent,
                    "reply_to": reply_to,
                },
            )
        )
        self._maybe_raise("send_message")
        return {"message_id": self.sent_message_id}

    def pin_chat_message(self, chat: str, message_id: int, silent: bool) -> None:
        self.calls.append(
            _Call(
                "pin_chat_message",
                {"chat": chat, "message_id": message_id, "silent": silent},
            )
        )
        self._maybe_raise("pin_chat_message")

    def unpin_chat_message(self, chat: str, message_id: int | None) -> None:
        self.calls.append(_Call("unpin_chat_message", {"chat": chat, "message_id": message_id}))
        self._maybe_raise("unpin_chat_message")
