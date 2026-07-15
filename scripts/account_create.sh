#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

print_usage() {
  cat <<EOF
Usage: $0 [options] <username> [email] [--superuser]

Create one local account and optionally grant superuser access.

EOF
  redmond_print_common_options
}

redmond_init "$@"
set -- "${redmond_wrapper_args[@]}"

if ((redmond_show_help == 1)); then
  print_usage
  exit 0
fi
if (($# < 1)) || (($# > 3)); then
  redmond_usage_error "Usage: $0 [options] <username> [email] [--superuser]"
fi

username="$1"
email=""
superuser_args=()

if (($# >= 2)); then
  case "$2" in
    --superuser)
      superuser_args=("--superuser")
      ;;
    *)
      email="$2"
      ;;
  esac
fi

if (($# == 3)); then
  if [[ "$3" != "--superuser" ]]; then
    redmond_usage_error \
      "Usage: $0 [options] <username> [email] [--superuser]"
  fi
  superuser_args=("--superuser")
fi

ensure_evennia
run_bootstrap account-create \
  --username "$username" \
  --email "$email" \
  "${superuser_args[@]}"
reload_evennia_runtime_if_running
