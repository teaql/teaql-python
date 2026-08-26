#!/usr/bin/env bash
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
expected=(conformance order-management school-management task_board)
mapfile -t actual < <(find "$repo/examples" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort)
if [[ "${actual[*]}" != "${expected[*]}" ]]; then
  echo "example inventory changed; update scripts/verify-examples.sh: ${actual[*]}" >&2
  exit 1
fi

PYTHONPATH="$repo/examples/conformance:$repo/src" python -m app.main
PYTHONPATH="$repo/examples/school-management:$repo/src" python -m app.main
PYTHONPATH="$repo/examples/order-management/python-lib-core:$repo/src" python "$repo/examples/order-management/python-app-console/app.py"
task_board_tmp="$(mktemp -d)"
trap 'rm -rf "$task_board_tmp"' EXIT
TEAQL_TASK_BOARD_DB="$task_board_tmp/task_board.db" PYTHONPATH="$repo/examples/task_board:$repo/src" python "$repo/examples/task_board/main.py"
echo "PASS: all Python examples"
