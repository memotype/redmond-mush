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

bootstrap_python_cmd() {
  if command -v python >/dev/null 2>&1; then
    printf '%s\n' python
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    printf '%s\n' python3
    return 0
  fi

  echo "python or python3 command not found. Activate the project virtualenv first." >&2
  exit 1
}

run_bootstrap() {
  local python_cmd
  python_cmd="$(bootstrap_python_cmd)"
  PYTHONPATH="$pythonpath_dir${PYTHONPATH:+:$PYTHONPATH}" \
    "$python_cmd" -m redmond_server.bootstrap "$@" --game-dir "$game_dir"
}

runtime_state_json() {
  run_bootstrap runtime-state
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

runtime_json_lines() {
  local mode="$1"
  local payload
  local python_cmd
  payload="$(runtime_state_json)"
  python_cmd="$(bootstrap_python_cmd)"
  "$python_cmd" -c '
from __future__ import annotations

import json
from pathlib import Path
import sys


def emit_present_flag_paths(data: dict[str, object]) -> int:
    game_dir = Path(str(data["game_dir"]))
    flags = data["restart_or_stop_flags"]
    assert isinstance(flags, dict)
    for name, exists in flags.items():
        if exists:
            print(game_dir / "server" / name)
    return 0


def emit_stale_pidfile_paths(data: dict[str, object]) -> int:
    game_dir = Path(str(data["game_dir"]))
    pidfiles = data["pidfiles"]
    assert isinstance(pidfiles, dict)
    for name, info in pidfiles.items():
        assert isinstance(info, dict)
        if info["exists"] and not info["process_running"]:
            print(game_dir / "server" / name)
    return 0


def emit_pidfile_pids(data: dict[str, object]) -> int:
    pidfiles = data["pidfiles"]
    assert isinstance(pidfiles, dict)
    for info in pidfiles.values():
        assert isinstance(info, dict)
        pid = info["pid"]
        if pid is not None:
            print(pid)
    return 0


def main() -> int:
    mode = sys.argv[1]
    data = json.load(sys.stdin)

    if mode == "runtime_markers_present":
        return 0 if data["runtime_marker_present"] else 1
    if mode == "runtime_processes_present":
        return 0 if data["running_process_count"] > 0 else 1
    if mode == "present_flag_paths":
        return emit_present_flag_paths(data)
    if mode == "stale_pidfile_paths":
        return emit_stale_pidfile_paths(data)
    if mode == "pidfile_pids":
        return emit_pidfile_pids(data)

    raise SystemExit(f"Unsupported runtime_json_lines mode: {mode}")


raise SystemExit(main())
' "$mode" <<<"$payload"
}

runtime_markers_present() {
  runtime_json_lines runtime_markers_present >/dev/null
}

remove_stale_runtime_files() {
  local path
  while IFS= read -r path; do
    [ -n "$path" ] && rm -f "$path"
  done < <(runtime_json_lines present_flag_paths)

  while IFS= read -r path; do
    [ -n "$path" ] && rm -f "$path"
  done < <(runtime_json_lines stale_pidfile_paths)
}

kill_pidfile_processes() {
  local signal="$1"
  local pid
  while IFS= read -r pid; do
    [ -n "$pid" ] || continue
    kill "-$signal" "$pid" >/dev/null 2>&1 || true
  done < <(runtime_json_lines pidfile_pids)
}

wait_for_runtime_shutdown() {
  local deadline
  deadline=$((SECONDS + shutdown_grace_seconds))

  while [ "$SECONDS" -lt "$deadline" ]; do
    if ! runtime_processes_present; then
      return 0
    fi
    sleep 1
  done

  return 1
}

runtime_processes_present() {
  runtime_json_lines runtime_processes_present >/dev/null
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
