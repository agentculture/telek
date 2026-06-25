"""Telegram integration package — Bot API client behind a sync façade."""

from telegram_agent.telegram._client import TelegramClient
from telegram_agent.telegram._config import TOKEN_ENV_VAR, load_token, redact
from telegram_agent.telegram._plan import (
    PinIntent,
    RosterIntent,
    SendIntent,
    ValidatedPlan,
)

__all__ = [
    "TOKEN_ENV_VAR",
    "load_token",
    "redact",
    "TelegramClient",
    "ValidatedPlan",
    "SendIntent",
    "PinIntent",
    "RosterIntent",
]
