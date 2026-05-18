#!/usr/bin/env bash
set -euo pipefail
# Send a Telegram message via `telek bot send`. Defaults to --json.
# Pass --apply to actually send (dry-run otherwise).

for arg in "$@"; do
  if [[ "$arg" == "--apply" ]]; then
    echo "sending real Telegram message; ctrl-c within 1s to abort" >&2
    sleep 1
    break
  fi
done

exec uv run telek bot send --json "$@"
