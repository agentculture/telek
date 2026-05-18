#!/usr/bin/env bash
set -euo pipefail
# Pin or unpin via `telek group pin`. Defaults to --json.
# Pass --apply to actually (un)pin (dry-run otherwise).

for arg in "$@"; do
  if [[ "$arg" == "--apply" ]]; then
    echo "pinning real Telegram message; ctrl-c within 1s to abort" >&2
    sleep 1
    break
  fi
done

exec uv run telek group pin --json "$@"
