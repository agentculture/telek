#!/usr/bin/env bash
set -euo pipefail
# List count + admins + bot self via `telek group roster`. Defaults to --json.
exec uv run telek group roster --json "$@"
