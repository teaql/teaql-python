#!/usr/bin/env bash
set -euo pipefail
example="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$example/../.." && pwd)"
if [[ -n "${TEAQL_CONTEXT_SPI_EVIDENCE_DIR:-}" ]]; then
  evidence="$TEAQL_CONTEXT_SPI_EVIDENCE_DIR"
  mkdir "$evidence"
else
  evidence="$(mktemp -d -t teaql-python-vendor-registration.XXXXXXXX)"
fi
evidence="$(cd "$evidence" && pwd)"
python="${PYTHON:-python3}"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$repo/src:$example/python-lib-core"
for phase in first restart; do
  "$python" -B "$example/python-app-console/app/main.py" "$evidence/suppliers.sqlite" "$phase" | tee "$evidence/$phase.log"
done
PYTHONPATH="$repo/src" "$python" -B "$example/main.py" | tee "$evidence/calibration.log"
