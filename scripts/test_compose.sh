#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
product_root="$(cd "$script_dir/.." && pwd)"
compose_env="${REDMOND_COMPOSE_ENV_FILE:-$product_root/compose.env}"
game_dir="/opt/redmond/src/redmond_server/game"
validation_project="redmond-verify-$(date +%s)-$$"
overlay_dir="$(mktemp -d)"
overlay_env="$overlay_dir/compose.validation.env"
http_probe_error="$overlay_dir/http_probe_error.txt"

if ! command -v docker >/dev/null 2>&1; then
  printf '%s\n' "docker command not found." >&2
  exit 1
fi

if [[ ! -f "$compose_env" ]]; then
  printf '%s\n' "Compose env file not found: $compose_env" >&2
  printf '%s\n' "Copy compose.env.example to compose.env first." >&2
  exit 1
fi

cat >"$overlay_env" <<'EOF'
REDMOND_TELNET_PORT=0
REDMOND_WEB_PORT=0
REDMOND_WEBSOCKET_PORT=0
EOF

compose() {
  env \
    -u REDMOND_TELNET_PORT \
    -u REDMOND_WEB_PORT \
    -u REDMOND_WEBSOCKET_PORT \
    docker compose \
      --project-name "$validation_project" \
      --env-file "$compose_env" \
      --env-file "$overlay_env" \
      "$@"
}

wait_for_postgres() {
  attempts=30
  while ((attempts > 0)); do
    if compose exec -T postgres \
      sh -lc 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
      >/dev/null 2>&1; then
      return 0
    fi
    attempts=$((attempts - 1))
    sleep 2
  done

  printf '%s\n' "PostgreSQL did not become healthy in time." >&2
  return 1
}

print_runtime_diagnostics() {
  echo "Runtime diagnostics for isolated Compose project: $validation_project" >&2
  echo "Compose status:" >&2
  compose ps >&2 || true
  echo "Recent service logs:" >&2
  compose logs --tail 100 redmond postgres >&2 || true
  echo "Published Redmond port mappings:" >&2
  compose port redmond 4000 >&2 || true
  compose port redmond 4001 >&2 || true
  compose port redmond 4002 >&2 || true
}

fail_post_start_check() {
  printf '%s\n' "$1" >&2
  print_runtime_diagnostics
  return 1
}

wait_for_http_ready() {
  attempts=30
  web_port="$(compose port redmond 4001 | awk -F: 'END {print $NF}')"

  while ((attempts > 0)); do
    if REDMOND_WEB_PORT_PROBE="$web_port" python3 - <<'PY' >"$http_probe_error" 2>&1
from __future__ import annotations

import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

port = os.environ["REDMOND_WEB_PORT_PROBE"]
url = f"http://127.0.0.1:{port}/"

try:
    with urlopen(url, timeout=5) as response:
        if response.status != 200:
            raise SystemExit(f"Unexpected HTTP status: {response.status}")
except (HTTPError, URLError, TimeoutError, ConnectionError, OSError) as exc:
    print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
    raise SystemExit(1)
PY
    then
      rm -f "$http_probe_error"
      return 0
    fi

    attempts=$((attempts - 1))
    if ((attempts > 0)); then
      sleep 2
    fi
  done

  final_reason="HTTP readiness check timed out."
  if [[ -s "$http_probe_error" ]]; then
    final_reason="$final_reason Final failure: $(tail -n 1 "$http_probe_error")"
  fi
  rm -f "$http_probe_error"
  fail_post_start_check "$final_reason"
}

cleanup() {
  compose down -v --remove-orphans >/dev/null 2>&1 || true
  rm -f "$overlay_env"
  rmdir "$overlay_dir" >/dev/null 2>&1 || true
}

trap 'cleanup' EXIT INT TERM

echo "Using isolated Compose project: $validation_project"
echo "Validating Compose config..."
compose config >/dev/null

echo "Building Redmond image..."
compose build

echo "Starting PostgreSQL..."
compose up -d postgres
wait_for_postgres

echo "Checking PostgreSQL-backed diagnostics..."
compose run --rm redmond \
  python -m redmond_server.bootstrap doctor \
  --game-dir "$game_dir" >/dev/null

echo "Running explicit bootstrap steps..."
compose run --rm redmond \
  python -m redmond_server.bootstrap migrate \
  --game-dir "$game_dir"
printf 'compose-admin-pass\n' | compose run --rm \
  -e REDMOND_TEST_PASSWORD_INPUT=1 redmond \
  python -m redmond_server.bootstrap ensure-superuser \
  --username compose-admin \
  --email compose-admin@example.com \
  --game-dir "$game_dir" >/dev/null
compose run --rm redmond \
  python -m redmond_server.bootstrap initial-setup \
  --game-dir "$game_dir" >/dev/null
compose run --rm redmond \
  python -m redmond_server.bootstrap seed \
  --game-dir "$game_dir" >/dev/null

echo "Starting Redmond service..."
compose up -d redmond
if ! compose exec -T redmond evennia status >/dev/null; then
  fail_post_start_check "Evennia status failed after initial Redmond startup."
fi
if ! compose exec -T redmond \
  python -m redmond_server.bootstrap doctor \
  --game-dir "$game_dir" >/dev/null; then
  fail_post_start_check "Bootstrap doctor failed after initial Redmond startup."
fi

echo "Checking local web connectivity..."
wait_for_http_ready

echo "Checking safe shutdown and volume-preserving restart..."
compose down
compose up -d postgres
wait_for_postgres
compose run --rm redmond \
  python -m redmond_server.bootstrap has-superuser \
  --game-dir "$game_dir" >/dev/null
compose run --rm redmond \
  python -m redmond_server.bootstrap doctor \
  --game-dir "$game_dir" >/dev/null
compose up -d redmond
if ! compose exec -T redmond evennia status >/dev/null; then
  fail_post_start_check "Evennia status failed after preserved-volume restart."
fi
wait_for_http_ready

echo "Cleaning up disposable Compose state..."
compose down -v --remove-orphans
trap - EXIT INT TERM
