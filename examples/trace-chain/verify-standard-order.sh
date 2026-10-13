#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
example="$repo/examples/trace-chain/standard-order"
evidence="$(mktemp -d -t teaql-python-standard-order.XXXXXXXX)"
echo "Python standard Order evidence: $evidence"
fingerprint() { (cd "$example/lib" && rg --files -g '*.py' | LC_ALL=C sort | xargs -d '\n' sha256sum); }
fingerprint > "$evidence/library-before.sha256"
for round in 1 2; do
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$example/lib:$repo/src" \
    TEAQL_STANDARD_ORDER_DB="$evidence/orders.sqlite" python3 "$example/main.py" > "$evidence/run-$round.log" 2>&1
  rg -q 'PYTHON_STANDARD_ORDER PASSED queries=4 counted=2 uncounted=2 total=3 preview=3 itemCount=5 facets=3' "$evidence/run-$round.log"
  if [[ "$round" == 1 ]]; then expected=4; else expected=0; fi
  rg -q "first_seed_audits=$expected repeat_seed_audits=0" "$evidence/run-$round.log"
  for name in TEAQL_TELEMETRY_ENABLED TEAQL_TELEMETRY_SERVICE_NAME TEAQL_TELEMETRY_OTLP_ENDPOINT; do rg -q "$name" "$evidence/run-$round.log"; done
  cat "$evidence/run-$round.log"
done
fingerprint > "$evidence/library-after.sha256"
cmp "$evidence/library-before.sha256" "$evidence/library-after.sha256"
echo 'PASS: Python standard complete Order twice without database cleanup; library unchanged'
