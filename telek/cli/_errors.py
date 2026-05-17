"""TelekError and exit-code policy.

Every failure inside telek raises :class:`TelekError`. The top-level
``main()`` catches it, formats via :mod:`telek.cli._output`, and exits with
:attr:`TelekError.code`. This guarantees:

* no Python traceback leaks to stderr (agent-first error rubric);
* every error has a structured shape ``{code, message, remediation}``;
* the exit-code policy is centralised in one place.
"""

from __future__ import annotations

from dataclasses import dataclass

# Exit-code policy:
# 0      = success
# 1      = user-input error (bad flag, missing required arg, unknown path)
# 2      = environment / setup error (tool not installed, file unreadable,
#          required env var missing — e.g. TELEK_BOT_TOKEN when a write
#          verb tries to commit)
# 3+     = reserved
EXIT_SUCCESS = 0
EXIT_USER_ERROR = 1
EXIT_ENV_ERROR = 2


@dataclass
class TelekError(Exception):
    """Structured error raised within telek; carries a remediation hint for agents."""

    code: int
    message: str
    remediation: str = ""

    def __post_init__(self) -> None:
        super().__init__(self.message)

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "message": self.message,
            "remediation": self.remediation,
        }
