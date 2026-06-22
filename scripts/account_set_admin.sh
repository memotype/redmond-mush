#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <username> <true|false>" >&2
  exit 1
fi

ensure_evennia
run_bootstrap account-set-superuser \
  --username "$1" \
  --value "$2"
reload_evennia_runtime_if_running
