#!/usr/bin/env bash

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
product_root="$(cd "$script_dir/.." && pwd)"
default_wrapper_config="$product_root/config/redmond.env"
default_game_dir="$product_root/src/redmond_server/game"
pythonpath_dir="$product_root/src"
game_dir=""
server_dir=""
stop_timeout_seconds=""
shutdown_grace_seconds=""
reload_timeout_seconds=""
redmond_show_help=0
redmond_wrapper_config_explicit=0
redmond_wrapper_config_loaded=0
redmond_wrapper_config_path=""
redmond_wrapper_args=()
redmond_wrapper_common_args=()

redmond_fail() {
  printf '%s\n' "$*" >&2
  return 1
}

redmond_trim_whitespace() {
  local text="$1"
  text="${text#"${text%%[![:space:]]*}"}"
  text="${text%"${text##*[![:space:]]}"}"
  printf '%s' "$text"
}

redmond_strip_optional_quotes() {
  local value="$1"
  if [ "${#value}" -ge 2 ]; then
    case "$value" in
      \"*\")
        value="${value:1:${#value}-2}"
        ;;
      \'*\')
        value="${value:1:${#value}-2}"
        ;;
    esac
  fi
  printf '%s' "$value"
}

redmond_print_common_options() {
  cat <<EOF
Common options:
  -c, --config PATH  Load wrapper config from PATH. When omitted, the wrapper
                     loads $default_wrapper_config if it exists.
  --help             Show this help message.
EOF
}

redmond_usage_error() {
  local usage="$1"
  {
    printf '%s\n' "$usage"
    printf '\n'
    redmond_print_common_options
  } >&2
  return 1
}

redmond_config_usage_error() {
  local option_name="$1"
  redmond_fail "$option_name requires a config path."
  return 1
}

redmond_resolve_path_from_pwd() {
  local caller_pwd="$1"
  local candidate="$2"
  if [[ "$candidate" = /* ]]; then
    printf '%s\n' "$candidate"
    return 0
  fi
  printf '%s\n' "$caller_pwd/$candidate"
}

redmond_load_config_file() {
  local config_path="$1"
  local config_dir
  local raw_line
  local line_number=0

  if [ ! -e "$config_path" ]; then
    redmond_fail "Config file not found: $config_path"
    return 1
  fi
  if [ ! -r "$config_path" ]; then
    redmond_fail "Config file is not readable: $config_path"
    return 1
  fi
  config_dir="${config_path%/*}"

  while IFS= read -r raw_line || [ -n "$raw_line" ]; do
    local trimmed
    local key
    local value
    line_number=$((line_number + 1))
    trimmed="$(redmond_trim_whitespace "$raw_line")"
    if [ -z "$trimmed" ]; then
      continue
    fi
    if [[ "$trimmed" = \#* ]]; then
      continue
    fi
    if [[ ! "$trimmed" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
      redmond_fail \
        "Invalid config line $line_number in $config_path. " \
        "Use KEY=value assignments only."
      return 1
    fi

    key="${trimmed%%=*}"
    value="${trimmed#*=}"
    value="$(redmond_strip_optional_quotes "$value")"
    printf -v "$key" '%s' "$value"
    export "$key=$value"
  done <"$config_path"

  redmond_resolve_config_path_var REDMOND_GAME_DIR "$config_dir"
  redmond_resolve_config_path_var REDMOND_BACKUP_DIR "$config_dir"
  redmond_resolve_config_command_var \
    REDMOND_PGBACKREST_COMMAND \
    "$config_dir"
  redmond_wrapper_config_loaded=1
}

redmond_resolve_config_path_var() {
  local variable_name="$1"
  local base_dir="$2"
  local variable_value="${!variable_name:-}"
  if [ -z "$variable_value" ]; then
    return 0
  fi
  if [[ "$variable_value" = /* ]]; then
    return 0
  fi
  printf -v "$variable_name" '%s' "$base_dir/$variable_value"
  export "$variable_name=${!variable_name}"
}

redmond_resolve_config_command_var() {
  local variable_name="$1"
  local base_dir="$2"
  local variable_value="${!variable_name:-}"
  if [ -z "$variable_value" ]; then
    return 0
  fi
  if [[ "$variable_value" = /* ]]; then
    return 0
  fi
  if [[ "$variable_value" != */* ]]; then
    return 0
  fi
  printf -v "$variable_name" '%s' "$base_dir/$variable_value"
  export "$variable_name=${!variable_name}"
}

redmond_init() {
  local caller_pwd
  caller_pwd="$(pwd -P)"
  redmond_show_help=0
  redmond_wrapper_config_explicit=0
  redmond_wrapper_config_loaded=0
  redmond_wrapper_config_path=""
  redmond_wrapper_args=()
  redmond_wrapper_common_args=()

  while [ "$#" -gt 0 ]; do
    case "$1" in
      -c)
        [ "$#" -ge 2 ] || redmond_config_usage_error "-c"
        redmond_wrapper_config_path="$2"
        redmond_wrapper_config_explicit=1
        shift 2
        ;;
      --config)
        [ "$#" -ge 2 ] || redmond_config_usage_error "--config"
        redmond_wrapper_config_path="$2"
        redmond_wrapper_config_explicit=1
        shift 2
        ;;
      --help)
        redmond_show_help=1
        shift
        ;;
      --)
        shift
        while [ "$#" -gt 0 ]; do
          redmond_wrapper_args+=("$1")
          shift
        done
        break
        ;;
      *)
        redmond_wrapper_args+=("$1")
        shift
        ;;
    esac
  done

  if [ "$redmond_show_help" -eq 1 ]; then
    return 0
  fi

  if [ -n "$redmond_wrapper_config_path" ]; then
    redmond_wrapper_config_path="$(
      redmond_resolve_path_from_pwd \
        "$caller_pwd" \
        "$redmond_wrapper_config_path"
    )"
    redmond_wrapper_common_args=(
      "--config"
      "$redmond_wrapper_config_path"
    )
    redmond_load_config_file "$redmond_wrapper_config_path" || return 1
  elif \
    [ -z "${REDMOND_WRAPPER_DISABLE_DEFAULT_CONFIG:-}" ] && \
    [ -f "$default_wrapper_config" ]
  then
    redmond_wrapper_config_path="$default_wrapper_config"
    redmond_load_config_file "$redmond_wrapper_config_path" || return 1
  fi

  game_dir="${REDMOND_GAME_DIR:-$default_game_dir}"
  server_dir="$game_dir/server"
  stop_timeout_seconds="${REDMOND_STOP_TIMEOUT_SECONDS:-20}"
  shutdown_grace_seconds="${REDMOND_SHUTDOWN_GRACE_SECONDS:-5}"
  reload_timeout_seconds="${REDMOND_RELOAD_TIMEOUT_SECONDS:-30}"
}

ensure_evennia() {
  if ! command -v evennia >/dev/null 2>&1; then
    printf '%s\n' \
      "evennia command not found. Activate the project virtualenv first." >&2
    return 1
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

  printf '%s\n' \
    "python or python3 command not found. Activate the project virtualenv first." >&2
  return 1
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

require_sqlite_local_recovery() {
  local python_cmd
  python_cmd="$(bootstrap_python_cmd)"
  REDMOND_GAME_DIR="$game_dir" \
  PYTHONPATH="$pythonpath_dir${PYTHONPATH:+:$PYTHONPATH}" \
    "$python_cmd" - <<'PY'
from __future__ import annotations

from pathlib import Path
import os
import sys

from redmond_server.game.server.conf import _database


game_dir = Path(os.environ["REDMOND_GAME_DIR"]).resolve()
metadata = _database.describe_database_config(game_dir=game_dir)
if metadata["engine"] != "sqlite":
    raise SystemExit(
        "SQLite-local recovery commands are available only for "
        "SQLite-backed dev/test runs. PostgreSQL production backup "
        "and restore are not implemented in this slice."
    )
PY
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
    cd "$game_dir" || return 1
    timeout "${reload_timeout_seconds}s" evennia reload >/dev/null 2>&1
  )
}

stop_evennia_runtime() {
  ensure_runtime_layout
  remove_stale_runtime_files

  if runtime_markers_present; then
    (
      cd "$game_dir" || return 1
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
