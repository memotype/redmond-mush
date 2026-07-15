#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

print_usage() {
  cat <<EOF
Usage: $0 [options]

Create one SQLite-local dev/test backup archive.

EOF
  redmond_print_common_options
}

redmond_init "$@"
set -- "${redmond_wrapper_args[@]}"

if ((redmond_show_help == 1)); then
  print_usage
  exit 0
fi
if (($# != 0)); then
  redmond_usage_error "Usage: $0 [options]"
fi

backup_dir="${REDMOND_BACKUP_DIR:-$game_dir/server/backups}"

ensure_evennia
require_sqlite_local_recovery

archive_path="$(run_bootstrap backup --backup-dir "$backup_dir")"
printf '%s\n' "Created backup: $archive_path"
