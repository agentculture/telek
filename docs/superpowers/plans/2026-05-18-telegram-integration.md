# Telegram Integration (v0.2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the three v0.2 Telegram verbs (`telegram-agent bot send`, `telegram-agent group roster`, `telegram-agent group pin`) behind a sync façade over `python-telegram-bot`, dry-run by default with validated-preview semantics, `.env`-aware token loading with redaction, and a vendored `.claude/skills/telegram/` wrapper.

**Architecture:** New `telegram_agent/telegram/` package owns Bot API work behind a small `TelegramClient` sync façade (asyncio.run over python-telegram-bot v21). CLI verbs in `telegram_agent/cli/_commands/bot.py` + `group.py` build a request, call `client.validate(plan)` to run read-only probes, then either print the validated plan (dry-run) or call the verb's mutation method (`--apply`). All errors funnel through `_errors.wrap()` → `TelegramAgentError`. Tests inject a `FakeTelegramClient` via dependency injection — no network mocks.

**Tech Stack:** Python ≥3.12, hatchling, argparse (existing), `python-telegram-bot>=21,<22` (new optional dep), pytest, no other runtime deps.

**Spec reference:** `docs/superpowers/specs/2026-05-18-telegram-integration-design.md`

---

## File Structure

**New files:**

- `telegram_agent/telegram/__init__.py` — re-exports public API (`TelegramClient`, `load_token`, `redact`, `ValidatedPlan`).
- `telegram_agent/telegram/_config.py` — `load_token()`, `_parse_env_file()`, `redact()`, `_find_dotenv_paths()`.
- `telegram_agent/telegram/_errors.py` — `wrap(exc) -> TelegramAgentError` mapping table.
- `telegram_agent/telegram/_plan.py` — `ValidatedPlan` dataclass + verb-specific `Intent` dataclasses + `to_dict()` serialization.
- `telegram_agent/telegram/_client.py` — `TelegramClient` sync façade with lazy `python-telegram-bot` import; defines `TelegramClientProtocol` for typing.
- `telegram_agent/cli/_commands/bot.py` — `register(sub)` + `_run_send(args)` for `telegram-agent bot send`.
- `telegram_agent/cli/_commands/group.py` — `register(sub)` + `_run_roster(args)` + `_run_pin(args)` for `telegram-agent group ...`.
- `tests/fakes.py` — `FakeTelegramClient` test double (recorded calls + canned returns).
- `tests/test_config.py` — token loading, .env precedence, redaction.
- `tests/test_errors.py` — `wrap()` mapping for each exception class.
- `tests/test_plan.py` — `ValidatedPlan.to_dict()` JSON shape per verb.
- `tests/test_telegram_cli.py` — CLI smoke for all three verbs (dry-run + --apply paths).
- `.claude/skills/telegram/SKILL.md` — agent-facing usage doc.
- `.claude/skills/telegram/scripts/send.sh` — wraps `telegram-agent bot send`.
- `.claude/skills/telegram/scripts/roster.sh` — wraps `telegram-agent group roster`.
- `.claude/skills/telegram/scripts/pin.sh` — wraps `telegram-agent group pin`.

**Modified files:**

- `telegram_agent/cli/__init__.py` — register the new `bot` and `group` noun groups.
- `pyproject.toml` — add `[project.optional-dependencies] telegram` + bump version to `0.2.0`.
- `CHANGELOG.md` — prepend `[0.2.0]` entry.
- `README.md` — add Telegram usage subsection + `.env` precedence note.
- `docs/skill-sources.md` — row noting `telegram` skill is original to telegram-agent.

---

## Task 1: Config — token loading, `.env` discovery, redaction

**Files:**

- Create: `telegram_agent/telegram/__init__.py`
- Create: `telegram_agent/telegram/_config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_config.py`:

```python
"""Tests for telegram_agent.telegram._config."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from telegram_agent.telegram._config import load_token, redact


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    monkeypatch.delenv("TELEGRAM_AGENT_BOT_TOKEN", raising=False)


def test_load_token_from_environ(monkeypatch):
    monkeypatch.setenv("TELEGRAM_AGENT_BOT_TOKEN", "env-token-123")
    assert load_token(cwd=Path("/tmp")) == "env-token-123"


def test_load_token_from_dotenv_in_cwd(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("TELEGRAM_AGENT_BOT_TOKEN=cwd-token\n")
    monkeypatch.delenv("TELEGRAM_AGENT_BOT_TOKEN", raising=False)
    assert load_token(cwd=tmp_path) == "cwd-token"


def test_load_token_environ_wins_over_dotenv(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("TELEGRAM_AGENT_BOT_TOKEN=file-token\n")
    monkeypatch.setenv("TELEGRAM_AGENT_BOT_TOKEN", "env-token")
    assert load_token(cwd=tmp_path) == "env-token"


def test_load_token_walks_up_to_git_root(tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".env").write_text("TELEGRAM_AGENT_BOT_TOKEN=root-token\n")
    nested = tmp_path / "a" / "b" / "c"
    nested.mkdir(parents=True)
    assert load_token(cwd=nested) == "root-token"


def test_load_token_missing_returns_none(tmp_path):
    assert load_token(cwd=tmp_path) is None


def test_dotenv_quoted_value(tmp_path):
    (tmp_path / ".env").write_text('TELEGRAM_AGENT_BOT_TOKEN="quoted value"\n')
    assert load_token(cwd=tmp_path) == "quoted value"


def test_dotenv_malformed_line_skipped(tmp_path, capsys):
    (tmp_path / ".env").write_text("not a key value line\nTELEGRAM_AGENT_BOT_TOKEN=ok\n")
    assert load_token(cwd=tmp_path) == "ok"


def test_dotenv_comments_and_blanks_ignored(tmp_path):
    (tmp_path / ".env").write_text("# comment\n\nTELEGRAM_AGENT_BOT_TOKEN=ok\n")
    assert load_token(cwd=tmp_path) == "ok"


def test_dotenv_world_writable_is_skipped(tmp_path, capsys):
    env_file = tmp_path / ".env"
    env_file.write_text("TELEGRAM_AGENT_BOT_TOKEN=insecure\n")
    env_file.chmod(0o646)
    assert load_token(cwd=tmp_path) is None
    err = capsys.readouterr().err
    assert "world" in err.lower() or "permission" in err.lower()


def test_redact_replaces_token():
    out = redact("the token is abc123 here", token="abc123")
    assert "abc123" not in out
    assert "***" in out


def test_redact_handles_none_token():
    assert redact("nothing to mask", token=None) == "nothing to mask"


def test_redact_handles_empty_token():
    assert redact("nothing to mask", token="") == "nothing to mask"


def test_redact_masks_all_occurrences():
    out = redact("abc abc abc", token="abc")
    assert "abc" not in out
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_config.py -v`
Expected: ImportError — `telegram_agent.telegram._config` does not exist yet.

- [ ] **Step 3: Implement `telegram_agent/telegram/_config.py`**

```python
"""Config: token loading from env or .env, with redaction.

Token source order (first match wins): process env, then .env in cwd, then
.env at the nearest enclosing git root. Process env always wins so CI
exports cannot be silently overridden by a stale .env.
"""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

TOKEN_ENV_VAR = "TELEGRAM_AGENT_BOT_TOKEN"


def _parse_env_file(path: Path) -> dict[str, str]:
    """Parse a .env file. Supports KEY=value and KEY="value with spaces".

    Skips blank lines, comments, and malformed lines. No interpolation,
    no multiline, no `export`.
    """
    result: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        result[key] = value
    return result


def _is_world_or_group_writable(path: Path) -> bool:
    if os.name != "posix":
        return False
    try:
        mode = path.stat().st_mode
    except OSError:
        return False
    return bool(mode & (stat.S_IWGRP | stat.S_IWOTH))


def _find_dotenv_paths(cwd: Path) -> list[Path]:
    """Return .env paths to check, in priority order: cwd, then git root."""
    paths: list[Path] = []
    cwd_env = cwd / ".env"
    if cwd_env.is_file():
        paths.append(cwd_env)

    current = cwd
    for _ in range(64):
        if (current / ".git").exists():
            root_env = current / ".env"
            if root_env.is_file() and root_env not in paths:
                paths.append(root_env)
            break
        if current.parent == current:
            break
        current = current.parent

    return paths


def load_token(cwd: Path | None = None) -> str | None:
    """Resolve TELEGRAM_AGENT_BOT_TOKEN from env or .env. Returns None if unset."""
    env_value = os.environ.get(TOKEN_ENV_VAR)
    if env_value:
        return env_value

    base = cwd if cwd is not None else Path.cwd()
    for env_path in _find_dotenv_paths(base):
        if _is_world_or_group_writable(env_path):
            print(
                f"warning: {env_path} has world- or group-writable permissions; "
                f"skipping for safety",
                file=sys.stderr,
            )
            continue
        parsed = _parse_env_file(env_path)
        if TOKEN_ENV_VAR in parsed and parsed[TOKEN_ENV_VAR]:
            return parsed[TOKEN_ENV_VAR]

    return None


def redact(text: str, token: str | None) -> str:
    """Mask every occurrence of token in text with '***'. No-op if token falsy."""
    if not token:
        return text
    return text.replace(token, "***")
```

Create `telegram_agent/telegram/__init__.py`:

```python
"""Telegram integration package — Bot API client behind a sync façade."""

from telegram_agent.telegram._config import TOKEN_ENV_VAR, load_token, redact

__all__ = ["TOKEN_ENV_VAR", "load_token", "redact"]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_config.py -v`
Expected: All 12 tests pass.

- [ ] **Step 5: Commit**

```bash
git add telegram_agent/telegram/__init__.py telegram_agent/telegram/_config.py tests/test_config.py
git commit -m "$(cat <<'EOF'
feat(telegram): token loader + .env discovery + redaction

Adds telegram_agent.telegram._config with TELEGRAM_AGENT_BOT_TOKEN resolution from
process env or .env (cwd then nearest git root). Process env wins.
World/group-writable .env files are skipped with a warning.
redact() masks token occurrences before any output crosses the wire.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Error mapping

**Files:**

- Create: `telegram_agent/telegram/_errors.py`
- Create: `tests/test_errors.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_errors.py`:

```python
"""Tests for telegram_agent.telegram._errors.wrap()."""

from __future__ import annotations

import pytest

from telegram_agent.cli._errors import EXIT_ENV_ERROR, EXIT_USER_ERROR
from telegram_agent.telegram._errors import wrap

telegram = pytest.importorskip("telegram")
from telegram.error import (  # noqa: E402
    BadRequest,
    Forbidden,
    InvalidToken,
    NetworkError,
    RetryAfter,
    TelegramError,
    TimedOut,
)


def test_invalid_token_maps_to_env_error():
    err = wrap(InvalidToken("Invalid token"), token=None)
    assert err.code == EXIT_ENV_ERROR
    assert "rejected" in err.message.lower() or "token" in err.message.lower()
    assert "BotFather" in err.remediation


def test_bad_request_chat_not_found_is_user_error():
    err = wrap(BadRequest("Chat not found"), token=None)
    assert err.code == EXIT_USER_ERROR
    assert "chat not found" in err.message.lower()
    assert "member" in err.remediation.lower()


def test_bad_request_no_rights_is_user_error():
    err = wrap(BadRequest("not enough rights to send messages"), token=None)
    assert err.code == EXIT_USER_ERROR
    assert "permission" in err.message.lower() or "rights" in err.message.lower()
    assert "promote" in err.remediation.lower()


def test_forbidden_bot_kicked_is_user_error():
    err = wrap(Forbidden("Forbidden: bot was kicked from the group chat"), token=None)
    assert err.code == EXIT_USER_ERROR
    assert "not in" in err.message.lower() or "chat" in err.message.lower()


def test_retry_after_is_env_error_with_seconds():
    exc = RetryAfter(retry_after=12)
    err = wrap(exc, token=None)
    assert err.code == EXIT_ENV_ERROR
    assert "12" in err.message
    assert "auto-retry" in err.remediation.lower() or "wait" in err.remediation.lower()


def test_network_error_is_env_error():
    err = wrap(NetworkError("connection reset"), token=None)
    assert err.code == EXIT_ENV_ERROR
    assert "network" in err.message.lower()


def test_timed_out_is_env_error():
    err = wrap(TimedOut(), token=None)
    assert err.code == EXIT_ENV_ERROR
    assert "network" in err.message.lower() or "timeout" in err.message.lower()


def test_other_bad_request_passes_through_as_user_error():
    err = wrap(BadRequest("Some unexpected detail"), token=None)
    assert err.code == EXIT_USER_ERROR
    assert "Some unexpected detail" in err.message


def test_other_telegram_error_is_env_error():
    err = wrap(TelegramError("Unknown server problem"), token=None)
    assert err.code == EXIT_ENV_ERROR
    assert "Unknown server problem" in err.message


def test_wrap_redacts_token_in_message():
    err = wrap(BadRequest("oops with abc123 leaked"), token="abc123")
    assert "abc123" not in err.message
    assert "***" in err.message


def test_wrap_passes_unknown_exception_through():
    err = wrap(RuntimeError("not a telegram error"), token=None)
    assert err.code == EXIT_ENV_ERROR
    assert "not a telegram error" in err.message
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_errors.py -v`
Expected: ImportError on `telegram_agent.telegram._errors`. (If `python-telegram-bot` is not installed, the `pytest.importorskip` will skip — install via `uv sync --extra telegram` after Task 7 lands. For now run `uv pip install 'python-telegram-bot>=21,<22'` in the dev env to exercise these tests.)

- [ ] **Step 3: Install python-telegram-bot for development**

Run: `uv pip install 'python-telegram-bot>=21,<22'`
Expected: Library installs into the project venv. (Task 7 makes this permanent via `pyproject.toml`; this step is bootstrap-only so tests can run.)

- [ ] **Step 4: Implement `telegram_agent/telegram/_errors.py`**

```python
"""Map python-telegram-bot exceptions to TelegramAgentError.

This module is the only place telegram.error exceptions cross into the rest
of telegram-agent. Every wrapped message is run through telegram_agent.telegram._config.redact
so a token accidentally embedded in an upstream string never escapes.
"""

from __future__ import annotations

from telegram_agent.cli._errors import EXIT_ENV_ERROR, EXIT_USER_ERROR, TelegramAgentError
from telegram_agent.telegram._config import redact


def wrap(exc: BaseException, *, token: str | None) -> TelegramAgentError:
    """Convert a python-telegram-bot exception into a TelegramAgentError."""
    from telegram.error import (
        BadRequest,
        Forbidden,
        InvalidToken,
        NetworkError,
        RetryAfter,
        TelegramError,
        TimedOut,
    )

    raw_msg = str(getattr(exc, "message", "") or str(exc))
    msg = redact(raw_msg, token)

    if isinstance(exc, InvalidToken):
        return TelegramAgentError(
            code=EXIT_ENV_ERROR,
            message="telegram rejected bot token",
            remediation="check TELEGRAM_AGENT_BOT_TOKEN with @BotFather",
        )

    if isinstance(exc, RetryAfter):
        seconds = getattr(exc, "retry_after", "?")
        return TelegramAgentError(
            code=EXIT_ENV_ERROR,
            message=f"rate limited; retry after {seconds}s",
            remediation="wait and retry; v0.2 does not auto-retry",
        )

    if isinstance(exc, (NetworkError, TimedOut)):
        return TelegramAgentError(
            code=EXIT_ENV_ERROR,
            message=f"network error talking to telegram: {msg}",
            remediation="check connectivity and retry",
        )

    if isinstance(exc, Forbidden):
        lowered = msg.lower()
        if "kicked" in lowered or "not a member" in lowered or "blocked" in lowered:
            return TelegramAgentError(
                code=EXIT_USER_ERROR,
                message="bot is not in this chat",
                remediation="add the bot to the chat first",
            )
        return TelegramAgentError(
            code=EXIT_USER_ERROR,
            message=f"forbidden: {msg}",
            remediation="check the bot has access to this chat",
        )

    if isinstance(exc, BadRequest):
        lowered = msg.lower()
        if "chat not found" in lowered:
            return TelegramAgentError(
                code=EXIT_USER_ERROR,
                message=f"chat not found: {msg}",
                remediation="verify id/username; ensure the bot is a member",
            )
        if "not enough rights" in lowered or "have no rights" in lowered:
            return TelegramAgentError(
                code=EXIT_USER_ERROR,
                message=f"bot lacks required permission: {msg}",
                remediation="promote the bot and grant the needed permission",
            )
        return TelegramAgentError(
            code=EXIT_USER_ERROR,
            message=msg,
            remediation="",
        )

    if isinstance(exc, TelegramError):
        return TelegramAgentError(
            code=EXIT_ENV_ERROR,
            message=msg,
            remediation="",
        )

    return TelegramAgentError(
        code=EXIT_ENV_ERROR,
        message=msg or exc.__class__.__name__,
        remediation="",
    )
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_errors.py -v`
Expected: All 11 tests pass.

- [ ] **Step 6: Commit**

```bash
git add telegram_agent/telegram/_errors.py tests/test_errors.py
git commit -m "$(cat <<'EOF'
feat(telegram): map python-telegram-bot exceptions to TelegramAgentError

Adds wrap(exc, token=...) as the only crossing point between telegram.error
and the rest of telegram-agent. Maps InvalidToken/RetryAfter/Network/Forbidden/
BadRequest with explicit remediation strings and the project's exit code
policy (user=1, env=2). Every message is redacted before it crosses.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: `ValidatedPlan` dataclass + verb intents

**Files:**

- Create: `telegram_agent/telegram/_plan.py`
- Create: `tests/test_plan.py`
- Modify: `telegram_agent/telegram/__init__.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_plan.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_plan.py -v`
Expected: ImportError on `telegram_agent.telegram._plan`.

- [ ] **Step 3: Implement `telegram_agent/telegram/_plan.py`**

```python
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
```

Update `telegram_agent/telegram/__init__.py`:

```python
"""Telegram integration package — Bot API client behind a sync façade."""

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
    "ValidatedPlan",
    "SendIntent",
    "PinIntent",
    "RosterIntent",
]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_plan.py -v`
Expected: All 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add telegram_agent/telegram/_plan.py telegram_agent/telegram/__init__.py tests/test_plan.py
git commit -m "$(cat <<'EOF'
feat(telegram): ValidatedPlan + per-verb Intent dataclasses

Adds frozen dataclasses ValidatedPlan, SendIntent, PinIntent, RosterIntent
with to_dict() serialization. Send previews truncate to 80 chars + ellipsis.
Roster intent embeds the "Bot API does not expose full member list" note.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: `TelegramClient` sync façade + FakeTelegramClient fixture

**Files:**

- Create: `telegram_agent/telegram/_client.py`
- Create: `tests/fakes.py`
- Modify: `telegram_agent/telegram/__init__.py`

- [ ] **Step 1: Write the FakeTelegramClient first** (no test yet; this is shared infrastructure used by Task 5+6 CLI tests)

Create `tests/fakes.py`:

```python
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
    """In-memory stand-in for telegram_agent.telegram.TelegramClient."""

    token: str | None = "fake-token"
    me: dict[str, Any] = field(
        default_factory=lambda: {"user_id": 42, "username": "fake_bot"}
    )
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
        self.calls.append(
            _Call("get_chat_member", {"chat": chat, "user_id": user_id})
        )
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
        self.calls.append(
            _Call("unpin_chat_message", {"chat": chat, "message_id": message_id})
        )
        self._maybe_raise("unpin_chat_message")
```

- [ ] **Step 2: Write client tests**

Create `tests/test_client.py`:

```python
"""Tests for telegram_agent.telegram._client.TelegramClient (lazy import + façade)."""

from __future__ import annotations

import pytest

from telegram_agent.cli._errors import EXIT_ENV_ERROR, TelegramAgentError


def test_client_requires_token():
    from telegram_agent.telegram._client import TelegramClient

    with pytest.raises(TelegramAgentError) as exc:
        TelegramClient(token=None)
    assert exc.value.code == EXIT_ENV_ERROR
    assert "TELEGRAM_AGENT_BOT_TOKEN" in exc.value.message


def test_client_missing_library_raises_clean(monkeypatch):
    """If python-telegram-bot can't import, TelegramClient raises TelegramAgentError."""
    import importlib
    import sys

    from telegram_agent.telegram import _client as client_mod

    monkeypatch.setitem(sys.modules, "telegram", None)
    importlib.reload(client_mod)

    with pytest.raises(TelegramAgentError) as exc:
        client_mod.TelegramClient(token="fake")
    assert exc.value.code == EXIT_ENV_ERROR
    assert "python-telegram-bot" in exc.value.message
    assert "telegram-agent[telegram]" in exc.value.remediation
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run pytest tests/test_client.py -v`
Expected: ImportError on `telegram_agent.telegram._client`.

- [ ] **Step 4: Implement `telegram_agent/telegram/_client.py`**

```python
"""Sync façade over python-telegram-bot.

CLI verbs stay synchronous (matching the existing learn/explain/whoami
pattern) by wrapping each async Bot method with asyncio.run. The lib is
imported lazily inside __init__ so `telegram-agent --help` and the non-Telegram
verbs work without the optional dep installed.
"""

from __future__ import annotations

import asyncio
from typing import Any

from telegram_agent.cli._errors import EXIT_ENV_ERROR, TelegramAgentError


class TelegramClient:
    """Synchronous façade over telegram.Bot."""

    def __init__(self, token: str | None) -> None:
        if not token:
            raise TelegramAgentError(
                code=EXIT_ENV_ERROR,
                message="TELEGRAM_AGENT_BOT_TOKEN not set",
                remediation=(
                    "set TELEGRAM_AGENT_BOT_TOKEN in your environment or a local .env file "
                    "(get the token from @BotFather)"
                ),
            )
        try:
            from telegram import Bot
        except ImportError as exc:
            raise TelegramAgentError(
                code=EXIT_ENV_ERROR,
                message="python-telegram-bot not installed",
                remediation="pip install 'telegram-agent[telegram]'",
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
```

Update `telegram_agent/telegram/__init__.py`:

```python
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
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_client.py -v`
Expected: Both tests pass. The "missing library" test reloads the module after blocking the import.

- [ ] **Step 6: Commit**

```bash
git add telegram_agent/telegram/_client.py telegram_agent/telegram/__init__.py tests/fakes.py tests/test_client.py
git commit -m "$(cat <<'EOF'
feat(telegram): TelegramClient sync façade + FakeTelegramClient

TelegramClient wraps python-telegram-bot v21 with asyncio.run, lazy-imports
telegram so `telegram-agent --help` works without the extra installed, and raises
TelegramAgentError cleanly when the lib or token is missing. FakeTelegramClient
satisfies the same protocol for tests — records calls, returns canned data,
supports raise_on={method: exception} for error-path coverage.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: `telegram-agent bot send` CLI verb

**Files:**

- Create: `telegram_agent/cli/_commands/bot.py`
- Modify: `telegram_agent/cli/__init__.py:51-66`
- Create: `tests/test_telegram_cli.py`

- [ ] **Step 1: Write the failing tests for `bot send`**

Create `tests/test_telegram_cli.py`:

```python
"""CLI smoke tests for telegram-agent bot/group verbs."""

from __future__ import annotations

import json
from typing import Any

import pytest

from telegram_agent.cli import main
from telegram_agent.cli._errors import EXIT_ENV_ERROR, EXIT_USER_ERROR
from tests.fakes import FakeTelegramClient

pytest.importorskip("telegram")
from telegram.error import BadRequest  # noqa: E402


@pytest.fixture
def fake(monkeypatch) -> FakeTelegramClient:
    client = FakeTelegramClient()
    monkeypatch.setenv("TELEGRAM_AGENT_BOT_TOKEN", "fake-token")
    monkeypatch.setattr(
        "telegram_agent.cli._commands.bot._build_client",
        lambda token: client,
    )
    monkeypatch.setattr(
        "telegram_agent.cli._commands.group._build_client",
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
    rc = main(
        ["bot", "send", "--chat", "@test", "--text", "hi", "--apply", "--json"]
    )
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
    monkeypatch.delenv("TELEGRAM_AGENT_BOT_TOKEN", raising=False)
    rc = main(["bot", "send", "--chat", "@x", "--text", "hi"])
    assert rc == EXIT_ENV_ERROR


def test_bot_send_chat_not_found_exits_user_error(fake, capsys):
    fake.raise_on["get_chat"] = BadRequest("Chat not found")
    rc = main(["bot", "send", "--chat", "@nope", "--text", "hi"])
    assert rc == EXIT_USER_ERROR


def test_bot_send_silent_flag_threaded_through(fake, capsys):
    rc = main(
        ["bot", "send", "--chat", "@x", "--text", "hi", "--silent", "--apply", "--json"]
    )
    assert rc == 0
    sent = [c for c in fake.calls if c.method == "send_message"]
    assert sent[0].kwargs["silent"] is True


def test_bot_send_reply_to_threaded_through(fake, capsys):
    rc = main(
        ["bot", "send", "--chat", "@x", "--text", "re", "--reply-to", "55",
         "--apply", "--json"]
    )
    assert rc == 0
    sent = [c for c in fake.calls if c.method == "send_message"]
    assert sent[0].kwargs["reply_to"] == 55
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_telegram_cli.py -v`
Expected: All fail with `argparse: invalid choice: 'bot'`.

- [ ] **Step 3: Implement `telegram_agent/cli/_commands/bot.py`**

```python
"""`telegram-agent bot ...` — bot-scoped Telegram verbs."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from telegram_agent.cli._errors import EXIT_USER_ERROR, TelegramAgentError
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
        "permissions": dict(member.get("permissions", {})),
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
) -> ValidatedPlan:
    try:
        me = client.get_me()
        chat = client.get_chat(args.chat)
        member = client.get_chat_member(args.chat, me["user_id"])
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
    return ValidatedPlan(
        verb="bot.send",
        chat=chat,
        bot_self=_bot_self_dict(me, member),
        intent=intent,
        dry_run=not args.apply,
    ), text


def _run_send(args: argparse.Namespace) -> int:
    token = load_token()
    client = _build_client(token)
    plan, text = _validate_send(client, args, token)

    if not args.apply:
        emit_result(plan.to_dict(), json_mode=args.json)
        return 0

    try:
        result = client.send_message(
            chat=args.chat,
            text=text,
            parse_mode=args.parse_mode,
            silent=args.silent,
            reply_to=args.reply_to,
        )
    except Exception as exc:
        raise wrap_telegram_error(exc, token=token) from exc

    out = plan.to_dict()
    out["dry_run"] = False
    out["message_id"] = result["message_id"]
    emit_result(out, json_mode=args.json)
    return 0


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
    send.add_argument("--silent", action="store_true")
    send.add_argument("--reply-to", type=int, default=None)
    send.add_argument("--apply", action="store_true", help="actually send")
    send.add_argument("--json", action="store_true")
    send.set_defaults(func=_run_send)
```

- [ ] **Step 4: Register `bot` group in `telegram_agent/cli/__init__.py`**

Open `telegram_agent/cli/__init__.py` and modify the `_build_parser` function. After the existing `_whoami_cmd.register(sub)` line, add the bot group:

```python
def _build_parser() -> argparse.ArgumentParser:
    from telegram_agent.cli._commands import bot as _bot_cmd
    from telegram_agent.cli._commands import explain as _explain_cmd
    from telegram_agent.cli._commands import learn as _learn_cmd
    from telegram_agent.cli._commands import whoami as _whoami_cmd

    parser = _TelegramAgentArgumentParser(
        prog="telegram-agent",
        description="telegram-agent — agent-first Telegram community management tools",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command", parser_class=_TelegramAgentArgumentParser)

    _learn_cmd.register(sub)
    _explain_cmd.register(sub)
    _whoami_cmd.register(sub)
    _bot_cmd.register(sub)

    return parser
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_telegram_cli.py -v -k "bot_send"`
Expected: All 9 `bot_send` tests pass.

- [ ] **Step 6: Commit**

```bash
git add telegram_agent/cli/_commands/bot.py telegram_agent/cli/__init__.py tests/test_telegram_cli.py
git commit -m "$(cat <<'EOF'
feat(cli): telegram-agent bot send (dry-run + --apply)

Adds `telegram-agent bot send` with --text / --text-stdin, --parse-mode (default
none), --silent, --reply-to, --apply, --json. Dry-run runs validated-
preview probes (getMe/getChat/getChatMember + permission asserts) and
prints the ValidatedPlan without sending. --apply flips dry_run=False
and calls send_message.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: `telegram-agent group roster` + `telegram-agent group pin` CLI verbs

**Files:**

- Create: `telegram_agent/cli/_commands/group.py`
- Modify: `telegram_agent/cli/__init__.py` — register `group` group
- Modify: `tests/test_telegram_cli.py` — append roster + pin tests

- [ ] **Step 1: Append failing tests for roster and pin to `tests/test_telegram_cli.py`**

Append to `tests/test_telegram_cli.py`:

```python
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
    rc = main(["group", "roster", "--chat", "@x", "--apply"])
    assert rc == EXIT_USER_ERROR  # --apply is not defined for roster


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
    rc = main(
        ["group", "pin", "--chat", "@x", "--message", "55", "--apply", "--json"]
    )
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
    rc = main(
        ["group", "pin", "--chat", "@x", "--unpin", "--message", "55",
         "--apply", "--json"]
    )
    assert rc == 0
    unpinned = [c for c in fake.calls if c.method == "unpin_chat_message"]
    assert unpinned[0].kwargs["message_id"] == 55


def test_group_pin_blocks_apply_when_bot_lacks_can_pin(fake, capsys):
    fake.bot_member = {
        "user_id": 42,
        "status": "administrator",
        "permissions": {"can_post": True, "can_pin": False},
    }
    rc = main(
        ["group", "pin", "--chat", "@x", "--message", "55", "--apply"]
    )
    assert rc == EXIT_USER_ERROR
    assert "pin_chat_message" not in [c.method for c in fake.calls]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_telegram_cli.py -v -k "group_"`
Expected: All fail with `argparse: invalid choice: 'group'`.

- [ ] **Step 3: Implement `telegram_agent/cli/_commands/group.py`**

```python
"""`telegram-agent group ...` — group-scoped Telegram verbs."""

from __future__ import annotations

import argparse
from typing import Any

from telegram_agent.cli._errors import EXIT_USER_ERROR, TelegramAgentError
from telegram_agent.cli._output import emit_result
from telegram_agent.telegram import (
    PinIntent,
    RosterIntent,
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
        "permissions": dict(member.get("permissions", {})),
    }


def _shared_probes(
    client: TelegramClient, chat_arg: str, token: str | None
) -> tuple[dict, dict, dict]:
    try:
        me = client.get_me()
        chat = client.get_chat(chat_arg)
        member = client.get_chat_member(chat_arg, me["user_id"])
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
        raise TelegramAgentError(
            code=EXIT_USER_ERROR,
            message="--message is required when pinning",
            remediation="pass --message <id> of the message to pin",
        )

    perms = member.get("permissions") or {}
    if member["status"] != "administrator" or not perms.get("can_pin"):
        raise TelegramAgentError(
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
    pin.add_argument("--silent", action="store_true")
    pin.add_argument("--unpin", action="store_true")
    pin.add_argument("--apply", action="store_true")
    pin.add_argument("--json", action="store_true")
    pin.set_defaults(func=_run_pin)
```

- [ ] **Step 4: Register `group` in `telegram_agent/cli/__init__.py`**

In `_build_parser`, add the `group` import and registration:

```python
def _build_parser() -> argparse.ArgumentParser:
    from telegram_agent.cli._commands import bot as _bot_cmd
    from telegram_agent.cli._commands import explain as _explain_cmd
    from telegram_agent.cli._commands import group as _group_cmd
    from telegram_agent.cli._commands import learn as _learn_cmd
    from telegram_agent.cli._commands import whoami as _whoami_cmd

    parser = _TelegramAgentArgumentParser(
        prog="telegram-agent",
        description="telegram-agent — agent-first Telegram community management tools",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command", parser_class=_TelegramAgentArgumentParser)

    _learn_cmd.register(sub)
    _explain_cmd.register(sub)
    _whoami_cmd.register(sub)
    _bot_cmd.register(sub)
    _group_cmd.register(sub)

    return parser
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_telegram_cli.py -v`
Expected: All tests pass — full bot_send + group_roster + group_pin coverage.

- [ ] **Step 6: Commit**

```bash
git add telegram_agent/cli/_commands/group.py telegram_agent/cli/__init__.py tests/test_telegram_cli.py
git commit -m "$(cat <<'EOF'
feat(cli): telegram-agent group roster + telegram-agent group pin

Roster: returns member_count, getChatAdministrators, bot self status +
permissions; explicit "Bot API does not expose full member list" note
in the payload. Pin: dry-run default; --apply gated on bot having
can_pin_messages; --unpin handles both targeted and current-pin cases.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Optional dependency declaration

**Files:**

- Modify: `pyproject.toml` (add `[project.optional-dependencies]` section)

- [ ] **Step 1: Add the optional extra**

Open `pyproject.toml`. After the `dependencies = []` line (around line 16), add:

```toml
[project.optional-dependencies]
telegram = ["python-telegram-bot>=21,<22"]
```

The full top of `pyproject.toml` should now look like:

```toml
[project]
name = "telegram-agent"
version = "0.1.0"
description = "Agent-first Telegram community management tools."
readme = "README.md"
license = "MIT"
requires-python = ">=3.12"
authors = [{name = "AgentCulture"}]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Programming Language :: Python :: 3.12",
    "License :: OSI Approved :: MIT License",
    "Topic :: Communications :: Chat",
    "Intended Audience :: Developers",
]
dependencies = []

[project.optional-dependencies]
telegram = ["python-telegram-bot>=21,<22"]
```

- [ ] **Step 2: Verify the extra resolves**

Run: `uv sync --extra telegram`
Expected: Resolves and installs `python-telegram-bot` and its deps into `.venv`.

- [ ] **Step 3: Verify the core install still works without the extra**

Run: `uv run python -c "import telegram_agent; print(telegram_agent.__version__)"`
Expected: prints `0.1.0`. (Version bump comes in Task 9.)

Run: `uv run python -c "from telegram_agent.telegram import TelegramClient; print('importable')"`
Expected: prints `importable` — the module imports fine even without instantiation.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "$(cat <<'EOF'
build: declare telegram optional extra

Adds python-telegram-bot>=21,<22 under [project.optional-dependencies]
telegram. Core install (pip install telegram-agent) stays zero-dep; users who
want the Telegram surface run pip install 'telegram-agent[telegram]'.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Vendored `.claude/skills/telegram/` wrapper

**Files:**

- Create: `.claude/skills/telegram/SKILL.md`
- Create: `.claude/skills/telegram/scripts/send.sh`
- Create: `.claude/skills/telegram/scripts/roster.sh`
- Create: `.claude/skills/telegram/scripts/pin.sh`
- Modify: `docs/skill-sources.md`

- [ ] **Step 1: Write `SKILL.md`**

Create `.claude/skills/telegram/SKILL.md`:

````markdown
---
name: telegram
description: Send messages, inspect group rosters, and pin messages via the Telegram Bot API through `telegram-agent`. Writes are dry-run by default; --apply is required to commit.
---

# telegram skill

Thin wrapper around `telegram-agent bot send` / `telegram-agent group roster` / `telegram-agent group pin`.
Scripts default to `--json` so agents get structured output without
remembering the flag.

## When to use

- Announcing in a chat or channel the bot is a member of.
- Pinning an announcement after sending it (capture `message_id` from the
  send response and pass it to `pin`).
- Auditing who has admin permissions in a group, plus the bot's own
  permissions, before write operations.

## Prerequisites

1. `pip install 'telegram-agent[telegram]'` — installs `python-telegram-bot`.
2. `TELEGRAM_AGENT_BOT_TOKEN` in environment or a local `.env` (cwd or repo root).
   Get a token by creating a bot with `@BotFather` on Telegram.
3. The bot must be a member of the target chat. For pin and most channel
   send cases, the bot must be promoted to admin with the relevant
   permission (`can_pin_messages`, `can_post_messages`).

## Verbs

| Script | Wraps | Side effect | Default |
|---|---|---|---|
| `send.sh` | `telegram-agent bot send` | sends a message | **dry-run** — pass `--apply` to actually send |
| `roster.sh` | `telegram-agent group roster` | read-only | runs |
| `pin.sh` | `telegram-agent group pin` | pins / unpins | **dry-run** — pass `--apply` to actually pin |

## Recipes

### Announce, then pin

```bash
MSG_ID=$(./scripts/send.sh --chat @announcements --text "Release v0.2 is out" \
  --parse-mode markdown --apply | jq -r .message_id)
./scripts/pin.sh --chat @announcements --message "$MSG_ID" --apply
```

### Print the admin list

```bash
./scripts/roster.sh --chat @announcements | jq '.intent.administrators'
```

## Anti-patterns

- **Never** commit `TELEGRAM_AGENT_BOT_TOKEN` or `.env`. The `.gitignore` covers
  `.env`; keep it that way.
- **Always** read the dry-run JSON before passing `--apply`. The validated
  plan tells you if the bot has the right permissions; `--apply` skipping
  that check defeats the purpose.
- **Do not poll** roster to track membership — the Bot API doesn't expose
  full member lists; you'll only re-read the count.
- **No GitHub-style signature** in Telegram messages. The `- telegram-agent (Claude)`
  trailer applies to GitHub posts, not Telegram chat messages.
````

- [ ] **Step 2: Write `scripts/send.sh`**

Create `.claude/skills/telegram/scripts/send.sh`:

```bash
#!/usr/bin/env bash
# Send a Telegram message via `telegram-agent bot send`. Defaults to --json.
# Pass --apply to actually send (dry-run otherwise).
set -euo pipefail

for arg in "$@"; do
  if [[ "$arg" == "--apply" ]]; then
    echo "sending real Telegram message; ctrl-c within 1s to abort" >&2
    sleep 1
    break
  fi
done

exec telegram-agent bot send --json "$@"
```

- [ ] **Step 3: Write `scripts/roster.sh`**

Create `.claude/skills/telegram/scripts/roster.sh`:

```bash
#!/usr/bin/env bash
# List count + admins + bot self via `telegram-agent group roster`. Defaults to --json.
set -euo pipefail
exec telegram-agent group roster --json "$@"
```

- [ ] **Step 4: Write `scripts/pin.sh`**

Create `.claude/skills/telegram/scripts/pin.sh`:

```bash
#!/usr/bin/env bash
# Pin or unpin via `telegram-agent group pin`. Defaults to --json.
# Pass --apply to actually (un)pin (dry-run otherwise).
set -euo pipefail

for arg in "$@"; do
  if [[ "$arg" == "--apply" ]]; then
    echo "pinning real Telegram message; ctrl-c within 1s to abort" >&2
    sleep 1
    break
  fi
done

exec telegram-agent group pin --json "$@"
```

- [ ] **Step 5: Make scripts executable**

Run: `chmod +x .claude/skills/telegram/scripts/*.sh`
Expected: No output, three scripts now have `-rwxr-xr-x` permissions.

- [ ] **Step 6: Verify scripts shell out without errors (no token needed; --help short-circuits)**

Run: `.claude/skills/telegram/scripts/send.sh --help`
Expected: prints `usage: telegram-agent bot send ...`

Run: `.claude/skills/telegram/scripts/roster.sh --help`
Expected: prints `usage: telegram-agent group roster ...`

Run: `.claude/skills/telegram/scripts/pin.sh --help`
Expected: prints `usage: telegram-agent group pin ...`

- [ ] **Step 7: Add provenance row to `docs/skill-sources.md`**

Open `docs/skill-sources.md`. Append (preserving the existing table shape):

```markdown
| `telegram` | original to telegram-agent (no upstream) | — | v0.2 |
```

If the table headers differ in this file, follow the existing column layout — the salient fact is: skill name = `telegram`, source = "original to telegram-agent", version = `v0.2`.

- [ ] **Step 8: Commit**

```bash
git add .claude/skills/telegram docs/skill-sources.md
git commit -m "$(cat <<'EOF'
skill(telegram): vendored agent wrapper for the v0.2 verbs

SKILL.md documents when to use, prerequisites, the three verbs, recipes
(announce-then-pin, print admin list), and anti-patterns. Scripts thinly
wrap `telegram-agent bot/group` with --json by default and a one-second stderr
warning before --apply on write verbs. No new tooling (bash, jq, telegram-agent).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: README + CHANGELOG + version bump

**Files:**

- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `pyproject.toml` (version: `0.1.0` → `0.2.0`)
- Modify: `telegram_agent/__init__.py` (`__version__` is derived from package metadata — verify no hardcoded version)

- [ ] **Step 1: Update `README.md` — Status section**

Find the `## Status` section in `README.md`. Replace the existing paragraph with:

```markdown
## Status

**Alpha.** v0.2 lands the Telegram surface: `telegram-agent bot send`,
`telegram-agent group roster`, `telegram-agent group pin`. Every write verb is dry-run by
default; pass `--apply` to commit.
```

- [ ] **Step 2: Update `README.md` — Usage section**

Find the `## Usage` section. After the existing usage block, append a new subsection:

````markdown
### Telegram verbs (requires `pip install 'telegram-agent[telegram]'`)

```bash
# read-only: count + admins + bot's own permissions
telegram-agent group roster --chat @announcements --json

# write (dry-run by default; --apply to commit)
telegram-agent bot send --chat @announcements --text "hello" --parse-mode markdown
telegram-agent bot send --chat @announcements --text "hello" --apply

# pin / unpin (also dry-run by default)
telegram-agent group pin --chat @announcements --message 123 --apply
telegram-agent group pin --chat @announcements --unpin --apply
```
````

- [ ] **Step 3: Update `README.md` — Configuration section**

In the `## Configuration` section, after the existing table, add:

```markdown
Tokens are loaded from `os.environ` first, then from a `.env` file in the
current directory, then from a `.env` at the nearest enclosing git root.
Process env always wins. `.env` files that are world- or group-writable
on POSIX are skipped with a warning.
```

- [ ] **Step 4: Bump version with the vendored skill**

Run: `python .claude/skills/version-bump/scripts/bump.py minor`
Expected: `pyproject.toml` bumps `0.1.0` → `0.2.0`; the script also prepends a `[Unreleased]` placeholder section to `CHANGELOG.md` (or handles the entry as configured — verify by reading the file).

- [ ] **Step 5: Write the `[0.2.0]` CHANGELOG entry**

Open `CHANGELOG.md`. Replace the most recent unreleased / placeholder entry with:

```markdown
## [0.2.0] - 2026-05-18

### Added

- Telegram surface (Bot API): `telegram-agent bot send`, `telegram-agent group roster`,
  `telegram-agent group pin`. Writes are dry-run by default; pass `--apply` to
  commit. Validated-preview dry-run runs `getMe`/`getChat`/
  `getChatMember` (plus per-verb permission asserts) before printing the
  plan, so foot-guns (invalid chat, missing permission, locked group)
  surface before any side effect.
- `TELEGRAM_AGENT_BOT_TOKEN` loading from environment or `.env` (cwd, then nearest
  git root; process env always wins). World/group-writable `.env` files
  are skipped with a warning.
- Vendored `.claude/skills/telegram/` agent wrapper (SKILL.md + send/roster/
  pin scripts).
- New optional dependency: `python-telegram-bot>=21,<22` under
  `[project.optional-dependencies] telegram`. Core install stays
  zero-dep; install with `pip install 'telegram-agent[telegram]'`.

### Notes

- `group roster` is bot-only by design; the Bot API does not expose full
  member lists. The response includes a `limits.note` reminding callers.
  MTProto support is deferred.
```

- [ ] **Step 6: Run the full local check suite**

Run all of the following in parallel where independent; sequentially otherwise:

```bash
uv sync --extra telegram
uv run pytest -n auto --cov=telegram_agent --cov-report=term -v
uv run black --check telegram_agent tests
uv run isort --check-only telegram_agent tests
uv run flake8 telegram_agent tests
uv run bandit -c pyproject.toml -r telegram_agent
uv run telegram-agent --version
```

Expected:

- pytest: all tests pass, coverage ≥ 60%.
- black / isort / flake8 / bandit: clean.
- `telegram-agent --version`: prints `telegram-agent 0.2.0`.

If black or isort complain, apply the fixes (`uv run black telegram_agent tests` / `uv run isort telegram_agent tests`) and re-commit just those fixups.

- [ ] **Step 7: Commit**

```bash
git add README.md CHANGELOG.md pyproject.toml
git commit -m "$(cat <<'EOF'
release: v0.2.0 — Telegram surface (bot send / group roster / group pin)

Bumps version to 0.2.0. README documents the new verbs and .env precedence;
CHANGELOG records the Telegram surface, dry-run default, .env loader,
skill wrapper, and the new optional [telegram] extra.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 8: Push the branch and open a PR**

Run:

```bash
git push -u origin design/telegram-integration
gh pr create --title "v0.2: Telegram surface (bot send / group roster / group pin)" \
  --body "$(cat <<'EOF'
## Summary

- Adds `telegram-agent bot send`, `telegram-agent group roster`, `telegram-agent group pin` over the Bot API.
- Dry-run by default on write verbs (`send`, `pin`); `--apply` required to commit.
- Validated-preview dry-run hits `getMe` / `getChat` / `getChatMember` and per-verb permission asserts before any side effect.
- `.env`-aware `TELEGRAM_AGENT_BOT_TOKEN` loading with redaction at the output chokepoint.
- Vendored `.claude/skills/telegram/` agent wrapper (SKILL.md + 3 scripts).
- `python-telegram-bot>=21,<22` added under `[project.optional-dependencies] telegram` — core install stays zero-dep.

## Test plan

- [ ] `uv run pytest -n auto --cov=telegram_agent --cov-report=term -v` — all green, coverage ≥ 60%.
- [ ] `uv run black --check telegram_agent tests && uv run isort --check-only telegram_agent tests && uv run flake8 telegram_agent tests` — clean.
- [ ] `uv run bandit -c pyproject.toml -r telegram_agent` — clean.
- [ ] `markdownlint-cli2 "**/*.md" "#node_modules"` — clean.
- [ ] Manual end-to-end against a real bot token + test chat: `telegram-agent bot send --chat <test> --text "hi"` (dry-run shape), then `--apply`.
- [ ] Manual: `telegram-agent group roster --chat <test> --json` returns the expected shape.
- [ ] Manual: `telegram-agent group pin --chat <test> --message <id> --apply` pins; `--unpin --apply` removes.

- telegram-agent (Claude)
EOF
)"
```

Expected: PR opened against `main` from `design/telegram-integration`.

---

## Self-review

**Spec coverage:**

- §2 In-scope: all three verbs ✓ (Tasks 5, 6); optional extra ✓ (Task 7); `.env` loading ✓ (Task 1); skill wrapper ✓ (Task 8); validated preview ✓ (Tasks 5, 6 via `_validate_send` / `_validate_pin` / `_shared_probes`); redaction ✓ (Task 1) + applied at error boundary (Task 2).
- §3 Architecture: module layout matches §3.1; sync façade ✓ (Task 4); optional dep ✓ (Task 7); lazy import in `TelegramClient.__init__` ✓ (Task 4).
- §4 CLI surface: flags, defaults, JSON shapes all match §4.1/§4.2/§4.3 ✓ (Tasks 5, 6).
- §5 Auth/redaction: env-first ✓; .env discovery in cwd then git root ✓; in-house ~20-line parser, no python-dotenv ✓; world/group-writable check ✓; redact chokepoint at output + at error wrapping ✓.
- §6 Validated preview: shared probes ✓ in `_shared_probes`; per-verb asserts in `_validate_send`/`_validate_pin` ✓; ValidatedPlan shape ✓ (Task 3); RetryAfter mapping ✓ (Task 2).
- §7 Skill wrapper: structure + SKILL.md sections + signature note + provenance row all in Task 8 ✓.
- §8 Error mapping: table matches Task 2 implementation ✓.
- §9 Testing strategy: FakeTelegramClient ✓ (Task 4); CLI smoke tests cover all dry-run + --apply paths + missing token + unknown chat + permission missing ✓ (Tasks 5, 6); redaction tests ✓ (Task 1); .env precedence + malformed + world-writable ✓ (Task 1).
- §10 Release: version bump + CHANGELOG + README all in Task 9 ✓.

**Placeholder scan:** No "TBD", "TODO", "implement later", or vague "add appropriate error handling". All code blocks contain real code. All commit messages real.

**Type consistency:** `bot_self` shape is `{user_id, status, permissions}` everywhere (Task 3 dataclass, Task 4 client serializer, Tasks 5/6 `_bot_self_dict`). `ValidatedPlan` constructor signature matches across all three callsites. `FakeTelegramClient` method signatures match `TelegramClient` real methods (`get_me`, `get_chat`, `get_chat_member`, `get_chat_member_count`, `get_chat_administrators`, `send_message`, `pin_chat_message`, `unpin_chat_message`). `_build_client` factory is the seam tests patch — defined identically in `bot.py` and `group.py`.

**Manual verification (optional, after merge):**

- With Playwright MCP + an open Telegram session, verify the `--apply` paths land messages / pins as expected in a test group.
- Verify `--json` payloads round-trip through `jq` cleanly.
