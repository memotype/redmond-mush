#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

if [ "$#" -lt 2 ] || [ "$#" -gt 4 ]; then
  echo "Usage: $0 <username> <password> [email] [--superuser]" >&2
  exit 1
fi

username="$1"
password="$2"
email=""
superuser_flag=""

if [ "$#" -ge 3 ]; then
  case "$3" in
    --superuser)
      superuser_flag="--superuser"
      ;;
    *)
      email="$3"
      ;;
  esac
fi

if [ "$#" -eq 4 ]; then
  if [ "$4" != "--superuser" ]; then
    echo "Usage: $0 <username> <password> [email] [--superuser]" >&2
    exit 1
  fi
  superuser_flag="--superuser"
fi

ensure_evennia
run_bootstrap account-create \
  --username "$username" \
  --password "$password" \
  --email "$email" \
  $superuser_flag
reload_evennia_runtime_if_running
