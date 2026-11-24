#!/usr/bin/env bash
set -euo pipefail
example="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$example/../.." && pwd)"
evidence="${TEAQL_INTERNAL_ID_EVIDENCE_DIR:-}"
if [[ -z "$evidence" ]]; then
  evidence="$(mktemp -d -t teaql-python-warehouse-ids.XXXXXXXX)"
else
  mkdir "$evidence"
fi
python="${PYTHON:-python3}"
export PYTHONPATH="$example/python-lib-core:$repo/src"
app="$example/python-app-console"
for phase in first restart; do
  "$python" -B "$app/app/main.py" "$evidence/warehouse.sqlite" "$phase" | tee "$evidence/$phase.log"
done
"$python" -B "$app/calibration/main.py" | tee "$evidence/calibration.log"
echo "PASS Warehouse orders and internal ID calibration. Evidence at $evidence"
