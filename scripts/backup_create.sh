#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

print_usage() {
  cat <<EOF
Usage: $0 [options]

Create one PostgreSQL full backup and emit JSON metadata.

EOF
  redmond_print_common_options
}

redmond_init "$@"
set -- "${redmond_wrapper_args[@]}"

if [ "$redmond_show_help" -eq 1 ]; then
  print_usage
  exit 0
fi
if [ "$#" -ne 0 ]; then
  redmond_usage_error "Usage: $0 [options]"
fi

run_bootstrap backup-create
