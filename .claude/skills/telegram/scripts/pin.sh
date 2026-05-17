#!/usr/bin/env bash
# Pin or unpin via `telek group pin`. Defaults to --json.
# Pass --apply to actually (un)pin (dry-run otherwise).
set -euo pipefail

for arg in "$@"; do
  if [[ "$arg" == "--apply" ]]; then
    echo "pinning real Telegram message; ctrl-c within 1s to abort" >&2
    sleep 1
    break
  fi
done

exec uv run telek group pin --json "$@"
