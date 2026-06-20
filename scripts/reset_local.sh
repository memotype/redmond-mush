#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_evennia

stop_evennia_runtime
rm -f "$game_dir/server/evennia.db3"

"$script_dir/init_local.sh"
