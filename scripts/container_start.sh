#!/bin/sh

set -eu

game_dir="${REDMOND_GAME_DIR:-/opt/redmond/src/redmond_server/game}"
launcher_pid=""

stop_runtime() {
  if [ -n "$launcher_pid" ]; then
    kill "$launcher_pid" >/dev/null 2>&1 || true
  fi
  cd "$game_dir"
  evennia stop >/dev/null 2>&1 || true
}

trap 'stop_runtime' EXIT INT TERM

cd "$game_dir"
evennia start -l &
launcher_pid="$!"
wait "$launcher_pid"
