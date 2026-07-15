#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

print_usage() {
  cat <<EOF
Usage: $0 [options] <username> <true|false>

Promote or demote one local account's admin role.

EOF
  redmond_print_common_options
}

redmond_init "$@"
set -- "${redmond_wrapper_args[@]}"

if ((redmond_show_help == 1)); then
  print_usage
  exit 0
fi
if (($# != 2)); then
  redmond_usage_error "Usage: $0 [options] <username> <true|false>"
fi

ensure_evennia
run_bootstrap account-set-superuser \
  --username "$1" \
  --value "$2"
reload_evennia_runtime_if_running
