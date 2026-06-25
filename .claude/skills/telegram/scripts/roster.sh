#!/usr/bin/env bash
set -euo pipefail
# List count + admins + bot self via `telegram-agent group roster`. Defaults to --json.
exec uv run telegram-agent group roster --json "$@"
