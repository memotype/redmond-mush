#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
product_root="$(cd "$script_dir/.." && pwd)"
default_game_dir="$product_root/src/redmond_server/game"
game_dir="${REDMOND_GAME_DIR:-$default_game_dir}"
pythonpath_dir="$product_root/src"
server_dir="$game_dir/server"
stop_timeout_seconds="${REDMOND_STOP_TIMEOUT_SECONDS:-20}"
shutdown_grace_seconds="${REDMOND_SHUTDOWN_GRACE_SECONDS:-5}"
reload_timeout_seconds="${REDMOND_RELOAD_TIMEOUT_SECONDS:-30}"

ensure_evennia() {
  if ! command -v evennia >/dev/null 2>&1; then
    echo "evennia command not found. Activate the project virtualenv first." >&2
    exit 1
  fi
}

run_bootstrap() {
  PYTHONPATH="$pythonpath_dir${PYTHONPATH:+:$PYTHONPATH}" \
    python -m redmond_server.bootstrap "$@" --game-dir "$game_dir"
}

runtime_pidfiles() {
  printf '%s\n' \
    "$server_dir/server.pid" \
    "$server_dir/portal.pid"
}

runtime_flag_files() {
  printf '%s\n' \
    "$server_dir/server.restart" \
    "$server_dir/portal.restart" \
    "$server_dir/server.stop" \
    "$server_dir/portal.stop"
}

ensure_runtime_layout() {
  mkdir -p "$server_dir/logs" "$server_dir/backups"
}

runtime_markers_present() {
  local path
  while IFS= read -r path; do
    if [ -e "$path" ]; then
      return 0
    fi
  done < <(runtime_flag_files)

  while IFS= read -r path; do
    if [ -e "$path" ]; then
      return 0
    fi
  done < <(runtime_pidfiles)

  return 1
}

remove_stale_runtime_files() {
  local path
  while IFS= read -r path; do
    [ -e "$path" ] && rm -f "$path"
  done < <(runtime_flag_files)

  while IFS= read -r path; do
    if [ ! -e "$path" ]; then
      continue
    fi
    if ! pid_is_running_from_pidfile "$path"; then
      rm -f "$path"
    fi
  done < <(runtime_pidfiles)
}

read_pidfile() {
  local pidfile="$1"
  if [ ! -f "$pidfile" ]; then
    return 1
  fi

  local pid
  pid="$(tr -d '[:space:]' <"$pidfile")"
  if [[ ! "$pid" =~ ^[0-9]+$ ]]; then
    return 1
  fi

  printf '%s\n' "$pid"
}

pid_is_running_from_pidfile() {
  local pidfile="$1"
  local pid
  if ! pid="$(read_pidfile "$pidfile")"; then
    return 1
  fi
  if ! kill -0 "$pid" >/dev/null 2>&1; then
    return 1
  fi

  local stat
  stat="$(ps -o stat= -p "$pid" 2>/dev/null | tr -d '[:space:]')"
  if [[ "$stat" == Z* ]]; then
    return 1
  fi

  return 0
}

kill_pidfile_processes() {
  local signal="$1"
  local path
  while IFS= read -r path; do
    local pid
    if ! pid="$(read_pidfile "$path")"; then
      continue
    fi
    kill "-$signal" "$pid" >/dev/null 2>&1 || true
  done < <(runtime_pidfiles)
}

wait_for_runtime_shutdown() {
  local deadline
  deadline=$((SECONDS + shutdown_grace_seconds))

  while [ "$SECONDS" -lt "$deadline" ]; do
    local path
    local any_running=0
    while IFS= read -r path; do
      if pid_is_running_from_pidfile "$path"; then
        any_running=1
        break
      fi
    done < <(runtime_pidfiles)

    if [ "$any_running" -eq 0 ]; then
      return 0
    fi
    sleep 1
  done

  return 1
}

runtime_processes_present() {
  local path
  while IFS= read -r path; do
    if pid_is_running_from_pidfile "$path"; then
      return 0
    fi
  done < <(runtime_pidfiles)

  return 1
}

reload_evennia_runtime_if_running() {
  ensure_runtime_layout
  remove_stale_runtime_files

  if ! runtime_processes_present; then
    return 0
  fi

  (
    cd "$game_dir"
    timeout "${reload_timeout_seconds}s" evennia reload >/dev/null 2>&1
  )
}

stop_evennia_runtime() {
  ensure_runtime_layout
  remove_stale_runtime_files

  if runtime_markers_present; then
    (
      cd "$game_dir"
      timeout "${stop_timeout_seconds}s" evennia stop >/dev/null 2>&1 || true
    )
  fi

  if wait_for_runtime_shutdown; then
    remove_stale_runtime_files
    return 0
  fi

  kill_pidfile_processes TERM
  if ! wait_for_runtime_shutdown; then
    kill_pidfile_processes KILL
    wait_for_runtime_shutdown || true
  fi

  remove_stale_runtime_files
}
