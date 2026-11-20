#!/usr/bin/env bash
set -euo pipefail
example="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$example/../.." && pwd)"
if [[ -n "${TEAQL_DISPATCH_PROFILE_EVIDENCE_DIR:-}" ]]; then
  evidence="$TEAQL_DISPATCH_PROFILE_EVIDENCE_DIR"
  mkdir "$evidence"
else
  evidence="$(mktemp -d -t teaql-python-dispatch-profile.XXXXXXXX)"
fi
evidence="$(cd "$evidence" && pwd)"
python="${PYTHON:-python3}"
export PYTHONDONTWRITEBYTECODE=1
for profile in camelCase snake_case PascalCase; do
  source="$example"
  if [[ "$profile" != camelCase ]]; then source="$example/profiles/$profile"; fi
  folder="$evidence/$profile"
  mkdir "$folder"
  for phase in first restart; do
    PYTHONPATH="$repo/src:$source/python-lib-core" "$python" -B "$source/python-app-console/app/main.py" "$folder/dispatch.sqlite" "$profile" "$phase" | tee "$folder/$phase.log"
  done
done
TEAQL_GENERATED_E_PROFILE_EVIDENCE_DIR="${TEAQL_GENERATED_E_PROFILE_EVIDENCE_DIR:-$evidence/calibration}" "$python" -B "$example/verify-local.py" | tee "$evidence/calibration.log"
