#!/usr/bin/env bash
set -euo pipefail
example="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$example/../.." && pwd)"
evidence="${TEAQL_TENANT_ORDER_POLICY_EVIDENCE_DIR:-}"
if [[ -z "$evidence" ]]; then
  evidence="$(mktemp -d -t teaql-python-tenant-order.XXXXXXXX)"
else
  mkdir "$evidence"
fi
export PYTHONPATH="$example/python-lib-core:$repo/src"
python="${PYTHON:-python3}"
app="$example/python-app-console"
for phase in first restart; do
  "$python" -B "$app/app/main.py" "$evidence/tenant-order.sqlite" "$phase" | tee "$evidence/$phase.log"
done
"$python" -B "$app/calibration/main.py" | tee "$evidence/calibration.log"
echo "PASS Tenant procurement and query policy calibration. Evidence at $evidence"
