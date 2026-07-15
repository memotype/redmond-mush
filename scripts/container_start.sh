#!/usr/bin/env bash

set -euo pipefail

game_dir="${REDMOND_GAME_DIR:-/opt/redmond/src/redmond_server/game}"
launcher_pid=""

stop_runtime() {
  if [[ -n "$launcher_pid" ]]; then
    kill "$launcher_pid" >/dev/null 2>&1 || true
  fi
  cd "$game_dir" || return 1
  evennia stop >/dev/null 2>&1 || true
}

cleanup() {
  stop_runtime || true
}

main() {
  trap cleanup EXIT INT TERM

  cd "$game_dir" || return 1
  evennia start -l &
  launcher_pid="$!"
  wait "$launcher_pid"
}

main "$@"
