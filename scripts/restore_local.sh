#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <backup-archive>" >&2
  exit 1
fi

archive_path="$1"

ensure_evennia
stop_evennia_runtime
run_bootstrap restore --archive "$archive_path"

if ! run_bootstrap seed >/dev/null; then
  echo "Restore completed, but reseed was deferred." >&2
  echo "Run ./scripts/status_local.sh and retry ./scripts/init_local.sh or" >&2
  echo "./scripts/reset_local.sh once the runtime is healthy again." >&2
fi

echo "Restored backup: $archive_path"
