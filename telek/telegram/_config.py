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

TOKEN_ENV_VAR = "TELEK_BOT_TOKEN"


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


def _is_world_writable(path: Path) -> bool:
    if os.name != "posix":
        return False
    try:
        mode = path.stat().st_mode
    except OSError:
        return False
    return bool(mode & stat.S_IWOTH)


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
    """Resolve TELEK_BOT_TOKEN from env or .env. Returns None if unset."""
    env_value = os.environ.get(TOKEN_ENV_VAR)
    if env_value:
        return env_value

    base = cwd if cwd is not None else Path.cwd()
    for env_path in _find_dotenv_paths(base):
        if _is_world_writable(env_path):
            print(
                f"warning: {env_path} is world-writable; skipping for safety",
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
