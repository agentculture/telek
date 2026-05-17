"""Allow running telek as ``python -m telek``."""

import sys

from telek.cli import main

if __name__ == "__main__":
    sys.exit(main())
