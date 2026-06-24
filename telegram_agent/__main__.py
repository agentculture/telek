"""Allow running telegram-agent as ``python -m telegram_agent``."""

import sys

from telegram_agent.cli import main

if __name__ == "__main__":
    sys.exit(main())
