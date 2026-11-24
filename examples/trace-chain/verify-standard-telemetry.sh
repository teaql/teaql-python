#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
evidence="${TEAQL_TRACE_CHAIN_STANDARD_EVIDENCE_DIR:-$(mktemp -d -t teaql-python-standard-example.XXXXXXXX)}"
mkdir -p "$evidence"
cd "$repo"
export PYTHONPATH="$repo/examples/trace-chain/python-lib-core:$repo/src"
export PYTHONDONTWRITEBYTECODE=1
fingerprint() { find examples/trace-chain/python-lib-core -type f -not -path '*/__pycache__/*' -print0 | sort -z | xargs -0 sha256sum; }
fingerprint > "$evidence/library-before.sha256"
for round in 1 2; do
  python examples/trace-chain/python-app-console/app/standard_telemetry.py > "$evidence/run-$round.log" 2>&1
  rg -q 'PYTHON_STANDARD_TELEMETRY_EXAMPLE PASSED first_seed_audits=1 repeat_seed_audits=0 queries=2 ordinary_sql_logs=0' "$evidence/run-$round.log"
  if [[ "${TEAQL_TELEMETRY_ENABLED:-false}" == "true" ]]; then
    rg -Fq 'TeaQL telemetry: enabled' "$evidence/run-$round.log"
  else
    for name in TEAQL_TELEMETRY_ENABLED TEAQL_TELEMETRY_SERVICE_NAME TEAQL_TELEMETRY_OTLP_ENDPOINT; do rg -q "$name" "$evidence/run-$round.log"; done
  fi
  cat "$evidence/run-$round.log"
done
fingerprint > "$evidence/library-after.sha256"
cmp "$evidence/library-before.sha256" "$evidence/library-after.sha256"
echo "PASS: Python standard telemetry example twice; generated library unchanged; evidence=$evidence"
