#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
example="$repo/examples/school-management"
evidence="$(mktemp -d -t teaql-python-bootstrap.XXXXXXXX)"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$example:$repo/src"
fingerprint() {
  { rg --files "$example/models" "$example/requests" -g '*.py'; printf '%s\n' "$example/Q.py" "$example/E.py" "$example/runtime_module.py"; } |
    LC_ALL=C sort | xargs -d '\n' sha256sum
}
fingerprint > "$evidence/library-before.sha256"
for logging in on off; do
  for round in 1 2; do
    TEAQL_SCHOOL_BOOTSTRAP_DB="$evidence/$logging.sqlite" TEAQL_SCHOOL_BOOTSTRAP_LOGGING="$logging" \
      python -m app.bootstrap_trace | tee "$evidence/$logging-$round.log"
    expected_logging=True; [[ "$logging" == off ]] && expected_logging=False
    fresh=True; version=1
    if [[ "$round" == 2 ]]; then fresh=False; version=3; fi
    rg -Fq "PASS Python generated bootstrap trace logging=$expected_logging fresh=$fresh originalVersion=$version" "$evidence/$logging-$round.log"
    fingerprint > "$evidence/library-after.sha256"
    cmp "$evidence/library-before.sha256" "$evidence/library-after.sha256"
  done
done
echo "PASS Python generated bootstrap twice per logging mode; retained evidence: $evidence"
