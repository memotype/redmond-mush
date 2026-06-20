#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

backup_dir="${REDMOND_BACKUP_DIR:-$game_dir/server/backups}"

ensure_evennia
run_bootstrap ensure-secret-settings >/dev/null

archive_path="$(run_bootstrap backup --backup-dir "$backup_dir")"
echo "Created backup: $archive_path"
