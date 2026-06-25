"""ValidatedPlan + verb-specific Intent dataclasses.

Every verb produces a ValidatedPlan after the shared probe sequence runs.
to_dict() serializes for both --json output and downstream consumption by
the --apply path; dry-run prints the dict directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

_TEXT_PREVIEW_MAX = 80


def _truncate(text: str, max_len: int = _TEXT_PREVIEW_MAX) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "…"


class Intent(Protocol):
    def to_dict(self) -> dict[str, Any]: ...


@dataclass(frozen=True)
class SendIntent:
    text_preview: str
    parse_mode: str  # "none" | "markdown" | "html"
    silent: bool
    reply_to: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "text_preview": _truncate(self.text_preview),
            "parse_mode": self.parse_mode,
            "silent": self.silent,
            "reply_to": self.reply_to,
        }


@dataclass(frozen=True)
class PinIntent:
    action: str  # "pin" | "unpin"
    message_id: int | None
    silent: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "message_id": self.message_id,
            "silent": self.silent,
        }


@dataclass(frozen=True)
class RosterIntent:
    member_count: int
    administrators: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "member_count": self.member_count,
            "administrators": list(self.administrators),
            "limits": {"note": "Bot API does not expose full member list"},
        }


@dataclass(frozen=True)
class ValidatedPlan:
    verb: str
    chat: dict[str, Any]
    bot_self: dict[str, Any]
    intent: Intent
    dry_run: bool
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "verb": self.verb,
            "chat": dict(self.chat),
            "bot_self": dict(self.bot_self),
            "intent": self.intent.to_dict(),
            "dry_run": self.dry_run,
            "warnings": list(self.warnings),
        }
