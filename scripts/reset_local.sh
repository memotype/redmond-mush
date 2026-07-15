#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

print_usage() {
  cat <<EOF
Usage: $0 [options]

Stop the local runtime, remove the SQLite database, and rerun init_local.

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

ensure_evennia
require_sqlite_local_recovery

stop_evennia_runtime
rm -f "$game_dir/server/evennia.db3"

"$script_dir/init_local.sh" "${redmond_wrapper_common_args[@]}"
