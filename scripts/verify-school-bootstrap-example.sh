#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
example="$repo/examples/school-management"
if [[ -n "${TEAQL_SCHOOL_BOOTSTRAP_EVIDENCE_DIR:-}" ]]; then
  evidence="$TEAQL_SCHOOL_BOOTSTRAP_EVIDENCE_DIR"
  mkdir "$evidence"
else
  evidence="$(mktemp -d -t teaql-python-bootstrap.XXXXXXXX)"
fi
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$example/python-app-console:$example/python-lib-core:$repo/src"
fingerprint() {
  { rg --files "$example/python-lib-core/models" "$example/python-lib-core/requests" -g '*.py'; printf '%s\n' "$example/python-lib-core/Q.py" "$example/python-lib-core/E.py" "$example/python-lib-core/runtime_module.py"; } |
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
