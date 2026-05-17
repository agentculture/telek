#!/usr/bin/env bash
# List count + admins + bot self via `telek group roster`. Defaults to --json.
set -euo pipefail
exec uv run telek group roster --json "$@"
