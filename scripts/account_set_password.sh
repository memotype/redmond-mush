#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

print_usage() {
  cat <<EOF
Usage: $0 [options] <username>

Reset the password for one local account.

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
  redmond_usage_error "Usage: $0 [options] <username>"
fi

ensure_evennia
run_bootstrap account-set-password \
  --username "$1"
reload_evennia_runtime_if_running
