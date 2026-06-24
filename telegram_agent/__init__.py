"""telegram-agent — Agent-first Telegram community management tools."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _v

try:
    __version__ = _v("telegram-agent")
except PackageNotFoundError:  # editable install without metadata
    __version__ = "0.0.0+local"

__all__ = ["__version__"]
