#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
product_root="$(cd "$script_dir/.." && pwd)"

cd "$product_root"
PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}" \
  python3 -m unittest \
  tests.test_smoke \
  tests.test_bootstrap_fast \
  tests.test_compose_contract \
  -v
