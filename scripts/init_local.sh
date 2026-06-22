#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

prompt_superuser_values() {
  if run_bootstrap has-superuser >/dev/null 2>&1; then
    return
  fi

  if [ -n "${EVENNIA_SUPERUSER_USERNAME:-}" ] && \
     [ -n "${EVENNIA_SUPERUSER_PASSWORD:-}" ]; then
    return
  fi

  read -r -p "Bootstrap superuser username: " EVENNIA_SUPERUSER_USERNAME
  read -r -p "Bootstrap superuser email (optional): " EVENNIA_SUPERUSER_EMAIL
  read -r -s -p "Bootstrap superuser password: " EVENNIA_SUPERUSER_PASSWORD
  echo
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
  --password "${EVENNIA_SUPERUSER_PASSWORD}" \
  --email "${EVENNIA_SUPERUSER_EMAIL:-}" >/dev/null

bootstrap_initial_world
run_bootstrap seed >/dev/null

echo "Redmond local bootstrap complete."
echo "Game dir: $game_dir"
