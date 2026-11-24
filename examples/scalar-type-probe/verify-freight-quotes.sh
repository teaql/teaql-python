#!/usr/bin/env bash
set -euo pipefail
example="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$example/../.." && pwd)"
evidence="${TEAQL_FREIGHT_QUOTE_EVIDENCE_DIR:-}"
if [[ -z "$evidence" ]]; then
  evidence="$(mktemp -d -t teaql-python-freight.XXXXXXXX)"
else
  mkdir "$evidence"
fi
evidence="$(cd "$evidence" && pwd)"
export PYTHONPATH="$example/python-lib-core:$repo/src" PYTHONDONTWRITEBYTECODE=1
python="${PYTHON:-python3}"
for phase in first restart; do
  "$python" "$example/python-app-console/app/main.py" "$evidence/freight.sqlite" "$phase" \
    | tee "$evidence/$phase.log"
done
mkdir "$evidence/calibration"
TEAQL_SCALAR_PROBE_DB="$evidence/calibration/scalar.sqlite" bash "$example/verify.sh" \
  | tee "$evidence/calibration/scalar.log"
for gate in restoration version empty; do
  bash "$example/verify-$gate.sh" "$evidence/calibration/$gate.sqlite" \
    | tee "$evidence/calibration/$gate.log"
done
echo "PASS Freight quotes and scalar calibrations. Evidence at $evidence"
