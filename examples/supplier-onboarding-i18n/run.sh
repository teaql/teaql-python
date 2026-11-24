#!/usr/bin/env bash
set -euo pipefail

example="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$example/../.." && pwd)"
python="${PYTHON:-python3}"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$example/python-lib-core:$repo/src"
exec "$python" "$example/run-example.py" --catalog "$example/python-lib-core/teaql-i18n.json" "$@" -- \
  "$python" "$example/python-app-console/app/main.py"
