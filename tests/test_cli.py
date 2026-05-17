"""Smoke tests for the telek CLI entry point."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from telek import __version__
from telek.cli import main


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert __version__ in out


def test_no_args_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main([])
    assert rc == 0
    out = capsys.readouterr().out
    assert "usage: telek" in out


def test_learn_text(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "telek" in out
    # Rubric: learn output must mention purpose, exit codes, --json, explain.
    assert "Exit-code policy" in out
    assert "--json" in out
    assert "explain" in out


def test_learn_json(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["learn", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["tool"] == "telek"
    assert payload["version"] == __version__
    assert payload["json_support"] is True
    assert "TELEK_BOT_TOKEN" in payload["env"]


def test_explain_root(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["explain"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "# telek" in out
    assert "Universal verbs" in out


def test_explain_known_path(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["explain", "whoami"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "telek whoami" in out
    assert "TELEK_BOT_TOKEN" in out


def test_explain_json(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["explain", "learn", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["path"] == ["learn"]
    assert "telek learn" in payload["markdown"]


def test_explain_unknown_path_errors(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["explain", "nonexistent"])
    assert rc == 1
    captured = capsys.readouterr()
    assert captured.err.startswith("error:")
    assert "hint:" in captured.err


def test_whoami_text(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.delenv("TELEK_BOT_TOKEN", raising=False)
    rc = main(["whoami"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "nick:" in out
    assert "bot_token_configured: false" in out


def test_whoami_nick_is_cwd_independent(
    monkeypatch: pytest.MonkeyPatch, tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`telek whoami` must report telek's nick regardless of CWD.

    Regression guard for the bug where `_read_nick()` resolved `culture.yaml`
    via the CWD — running `telek whoami` from a sibling repo would then
    report the *sibling's* nick. The fix walks up from `__file__` to find
    telek's own `culture.yaml`; this test sets the CWD to a directory
    containing a decoy `culture.yaml` with a different suffix and asserts
    whoami still resolves to `telek`.
    """
    monkeypatch.delenv("TELEK_BOT_TOKEN", raising=False)
    (tmp_path / "culture.yaml").write_text(
        "agents:\n- suffix: not-telek\n  backend: claude\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    rc = main(["whoami", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["nick"] == "telek"


def test_whoami_json_token_set(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("TELEK_BOT_TOKEN", "fake-token")
    rc = main(["whoami", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["version"] == __version__
    assert payload["bot_token_configured"] is True
    # Token value never leaks into the report.
    assert "fake-token" not in json.dumps(payload)
    assert set(payload.keys()) == {"nick", "version", "bot_token_configured"}


def test_unknown_verb_errors(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["bogus"])
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert err.startswith("error:")
    assert "hint:" in err


def test_python_dash_m_invocation() -> None:
    """`python -m telek --version` exits 0 and prints the version."""
    result = subprocess.run(
        [sys.executable, "-m", "telek", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert __version__ in result.stdout
