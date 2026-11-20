#!/usr/bin/env bash
set -euo pipefail
example="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$example/../.." && pwd)"
python="${PYTHON:-python}"
evidence="${TEAQL_REFERENCE_EVIDENCE_DIR:-}"
if [[ -n "$evidence" ]]; then
  [[ "$evidence" == /* ]]
  mkdir -- "$evidence"
else
  evidence="$(mktemp -d -t teaql-python-reference.XXXXXXXX)"
  trap 'rm -rf -- "$evidence"' EXIT
fi
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$example/python-lib-core:$example/python-app-console:$repo/src"
export TEAQL_DATABASE_CONNECTION_STRING="$evidence/orders.sqlite"
cd "$example"
"$python" main.py >"$evidence/portable-vector.log"
rg -Fx 'PASS: Python opaque entity reference' "$evidence/portable-vector.log"
for round in 1 2; do
  TEAQL_SHOWCASE_ROUND="$round" "$python" -m app.main >"$evidence/round-$round.log" 2>&1 || {
    tail -60 "$evidence/round-$round.log" >&2
    exit 1
  }
  rg '^ORDER_REFERENCE=' "$evidence/round-$round.log"
done
