"""Tests for telegram_agent.telegram._config."""

from __future__ import annotations

import os
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
    env_file = tmp_path / ".env"
    env_file.write_text("TELEGRAM_AGENT_BOT_TOKEN=cwd-token\n")
    if os.name == "posix":
        env_file.chmod(0o600)
    monkeypatch.delenv("TELEGRAM_AGENT_BOT_TOKEN", raising=False)
    assert load_token(cwd=tmp_path) == "cwd-token"


def test_load_token_environ_wins_over_dotenv(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("TELEGRAM_AGENT_BOT_TOKEN=file-token\n")
    monkeypatch.setenv("TELEGRAM_AGENT_BOT_TOKEN", "env-token")
    assert load_token(cwd=tmp_path) == "env-token"


def test_load_token_walks_up_to_git_root(tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()
    env_file = tmp_path / ".env"
    env_file.write_text("TELEGRAM_AGENT_BOT_TOKEN=root-token\n")
    if os.name == "posix":
        env_file.chmod(0o600)
    nested = tmp_path / "a" / "b" / "c"
    nested.mkdir(parents=True)
    assert load_token(cwd=nested) == "root-token"


def test_load_token_missing_returns_none(tmp_path):
    assert load_token(cwd=tmp_path) is None


def test_dotenv_quoted_value(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text('TELEGRAM_AGENT_BOT_TOKEN="quoted value"\n')
    if os.name == "posix":
        env_file.chmod(0o600)
    assert load_token(cwd=tmp_path) == "quoted value"


def test_dotenv_malformed_line_skipped(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("not a key value line\nTELEGRAM_AGENT_BOT_TOKEN=ok\n")
    if os.name == "posix":
        env_file.chmod(0o600)
    assert load_token(cwd=tmp_path) == "ok"


def test_dotenv_comments_and_blanks_ignored(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("# comment\n\nTELEGRAM_AGENT_BOT_TOKEN=ok\n")
    if os.name == "posix":
        env_file.chmod(0o600)
    assert load_token(cwd=tmp_path) == "ok"


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission bits required")
def test_dotenv_world_or_group_writable_is_skipped(tmp_path, capsys):
    env_file = tmp_path / ".env"
    env_file.write_text("TELEGRAM_AGENT_BOT_TOKEN=insecure\n")
    env_file.chmod(0o646)
    assert load_token(cwd=tmp_path) is None
    err = capsys.readouterr().err
    assert "world" in err.lower() or "permission" in err.lower()


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission bits required")
def test_dotenv_group_writable_is_skipped(tmp_path, capsys):
    env_file = tmp_path / ".env"
    env_file.write_text("TELEGRAM_AGENT_BOT_TOKEN=group-insecure\n")
    env_file.chmod(0o664)
    assert load_token(cwd=tmp_path) is None
    err = capsys.readouterr().err
    assert "world" in err.lower() or "group" in err.lower() or "permission" in err.lower()


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
