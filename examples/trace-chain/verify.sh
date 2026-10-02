#!/usr/bin/env bash
set -euo pipefail
example="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$example/../.." && pwd)"
if [[ -z "${TEAQL_TRACE_CHAIN_DB:-}" ]]; then
  trace_test_directory="$(mktemp -d)"
  export TEAQL_TRACE_CHAIN_DB="$trace_test_directory/trace-chain.sqlite"
fi
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$example/lib:$repo/src${PYTHONPATH:+:$PYTHONPATH}"
snapshot="$(mktemp)"
(cd "$example/lib" && find . -type f ! -path '*/__pycache__/*' -print0 | sort -z | xargs -0 sha256sum) > "$snapshot"
for attempt in first second; do
  echo "Run $attempt on $TEAQL_TRACE_CHAIN_DB without cleanup"
  python "$example/main.py"
done
(cd "$example/lib" && sha256sum --check "$snapshot")
echo "PASS: two runs on the same database; generated library hashes unchanged"
