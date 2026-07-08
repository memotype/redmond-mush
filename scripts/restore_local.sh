#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

print_usage() {
  cat <<EOF
Usage: $0 [options] <backup-archive>

Restore one SQLite-local dev/test backup archive.

EOF
  redmond_print_common_options
}

redmond_init "$@"
set -- "${redmond_wrapper_args[@]}"

if [ "$redmond_show_help" -eq 1 ]; then
  print_usage
  exit 0
fi
if [ "$#" -ne 1 ]; then
  redmond_usage_error "Usage: $0 [options] <backup-archive>"
fi

archive_path="$1"

ensure_evennia
require_sqlite_local_recovery
stop_evennia_runtime
run_bootstrap restore --archive "$archive_path"

if ! run_bootstrap seed >/dev/null; then
  echo "Restore completed, but reseed was deferred." >&2
  echo "Run ./scripts/status_local.sh and retry ./scripts/init_local.sh or" >&2
  echo "./scripts/reset_local.sh once the runtime is healthy again." >&2
fi

echo "Restored backup: $archive_path"
