#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

print_usage() {
  cat <<EOF
Usage: $0 [options]

Bootstrap the local SQLite-backed development game dir.

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

prompt_superuser_values() {
  if run_bootstrap has-superuser >/dev/null 2>&1; then
    return
  fi

  if [ -n "${EVENNIA_SUPERUSER_PASSWORD:-}" ]; then
    echo "EVENNIA_SUPERUSER_PASSWORD is no longer supported." >&2
    echo "Use the interactive password prompt, or stdin with REDMOND_TEST_PASSWORD_INPUT=1 for automated tests." >&2
    exit 1
  fi

  if [ -z "${EVENNIA_SUPERUSER_USERNAME:-}" ]; then
    read -r -p "Bootstrap superuser username: " EVENNIA_SUPERUSER_USERNAME
  fi
  if [ -z "${EVENNIA_SUPERUSER_EMAIL:-}" ]; then
    read -r -p "Bootstrap superuser email (optional): " EVENNIA_SUPERUSER_EMAIL
  fi
}

bootstrap_initial_world() {
  if ! run_bootstrap needs-initial-start >/dev/null 2>&1; then
    return
  fi

  run_bootstrap initial-setup >/dev/null
}

ensure_evennia
run_bootstrap ensure-secret-settings >/dev/null
ensure_runtime_layout

if ! run_bootstrap migrate >/dev/null; then
  echo "Evennia migrate failed for $game_dir." >&2
  echo "Run ./scripts/status_local.sh for diagnostics or ./scripts/reset_local.sh to rebuild local state." >&2
  exit 1
fi

prompt_superuser_values
run_bootstrap ensure-superuser \
  --username "${EVENNIA_SUPERUSER_USERNAME}" \
  --email "${EVENNIA_SUPERUSER_EMAIL:-}" >/dev/null

bootstrap_initial_world
run_bootstrap seed >/dev/null

echo "Redmond local bootstrap complete."
echo "Game dir: $game_dir"
