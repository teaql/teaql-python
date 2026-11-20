#!/usr/bin/env bash
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
expected=(business-clock business-id conformance context-derived expression-profiles facet-trace fix-e-alignment internal-id mutation-policy natural-messages object-storage opaque-entity-reference order-management query-policy scalar-type-probe school-management task_board trace-chain typed-extension-spi)
mapfile -t actual < <(find "$repo/examples" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort)
if [[ "${actual[*]}" != "${expected[*]}" ]]; then
  echo "example inventory changed; update scripts/verify-examples.sh: ${actual[*]}" >&2
  exit 1
fi

# A complete inventory run owns fresh data paths; never reset a developer's
# pre-existing .local database. Retain small databases/logs as evidence rather
# than confusing them with disposable compiler or dependency outputs.
if [[ -n "${TEAQL_EXAMPLES_EVIDENCE_DIR:-}" ]]; then
  evidence_directory="$TEAQL_EXAMPLES_EVIDENCE_DIR"
  [[ "$evidence_directory" == /* && ! -e "$evidence_directory" ]]
  mkdir -p -- "$evidence_directory"
else
  evidence_directory="$(mktemp -d -t teaql-python-examples-evidence.XXXXXXXX)"
fi
export TEAQL_CONFORMANCE_DB="$evidence_directory/conformance.sqlite"
export TEAQL_MANAGED_CREATION_DB="$evidence_directory/managed-creation.sqlite"
export TEAQL_SCHOOL_MANAGEMENT_DB="$evidence_directory/school.sqlite"
export TEAQL_SCALAR_PROBE_DB="$evidence_directory/scalar.sqlite"
export TEAQL_FIX_E_EVIDENCE_DIR="$evidence_directory/fix-e"
echo "Retained compact Python example inventory evidence: $evidence_directory"

python "$repo/scripts/verify_generated_runtime_boundary.py" "$repo/examples"
if rg -l 'include\s*=.*teaql\*' "$repo/examples" --glob pyproject.toml >/dev/null; then
  echo 'generated example package discovery must not include an embedded teaql namespace' >&2
  exit 1
fi

bash "$repo/examples/object-storage/verify.sh"
bash "$repo/examples/scalar-type-probe/verify.sh"
bash "$repo/examples/scalar-type-probe/verify-restoration.sh" "$evidence_directory/restoration.sqlite"
bash "$repo/examples/scalar-type-probe/verify-version.sh" "$evidence_directory/version.sqlite"
bash "$repo/examples/scalar-type-probe/verify-empty.sh" "$evidence_directory/empty-aggregates.sqlite"
python "$repo/examples/fix-e-alignment/verify-local.py"
TEAQL_CONTEXT_FIX_EVIDENCE_DIR="$evidence_directory/context-derived" python "$repo/examples/context-derived/verify-local.py"
TEAQL_NATURAL_MESSAGES_EVIDENCE_DIR="$evidence_directory/natural-messages" python "$repo/examples/natural-messages/verify-local.py"
TEAQL_GENERATED_E_PROFILE_EVIDENCE_DIR="$evidence_directory/expression-profiles" \
  python "$repo/examples/expression-profiles/verify-local.py"
TEAQL_CONFORMANCE_EVIDENCE_DIR="$evidence_directory/conformance" bash "$repo/examples/conformance/verify.sh"
PYTHONPATH="$repo/examples/school-management/python-app-console:$repo/src" python -m app.main
bash "$repo/scripts/verify-school-bootstrap-example.sh"
PYTHONPATH="$repo/src" python -m unittest discover -s "$repo/examples/school-management/python-app-console" -p 'test_sql_log_intent.py' -v
PYTHONPATH="$repo/src" python "$repo/examples/mutation-policy/python-app-console/calibration/main.py"
TEAQL_SHOWCASE_ROUND=inventory TEAQL_DATABASE_CONNECTION_STRING="$evidence_directory/customer-approval.sqlite" \
PYTHONPATH="$repo/src:$repo/examples/mutation-policy/python-lib-core" python "$repo/examples/mutation-policy/python-app-console/app/main.py"
PYTHONPATH="$repo/src" python "$repo/examples/business-clock/python-app-console/calibration/main.py"
TEAQL_DELIVERY_ORDER_ROUND=inventory TEAQL_DATABASE_CONNECTION_STRING="$evidence_directory/business-clock.sqlite" \
PYTHONPATH="$repo/src:$repo/examples/business-clock/python-lib-core" python "$repo/examples/business-clock/python-app-console/app/main.py"
PYTHONPATH="$repo/src" python "$repo/examples/business-id/python-app-console/calibration/main.py"
TEAQL_BUSINESS_ID_KEY_V1_HEX=000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f \
TEAQL_PURCHASE_NUMBERING_ROUND=inventory TEAQL_DATABASE_CONNECTION_STRING="$evidence_directory/business-id.sqlite" \
PYTHONPATH="$repo/src:$repo/examples/business-id/python-lib-core" python "$repo/examples/business-id/python-app-console/app/main.py"
PYTHONPATH="$repo/src" python "$repo/examples/internal-id/main.py"
PYTHONPATH="$repo/src" python "$repo/examples/typed-extension-spi/main.py"
PYTHONPATH="$repo/src" python "$repo/examples/query-policy/main.py"
PYTHONPATH="$repo/src" python "$repo/examples/opaque-entity-reference/main.py"
TEAQL_ORDER_EVIDENCE_DIR="$evidence_directory/order-management" bash "$repo/examples/order-management/verify.sh"
TEAQL_TASK_BOARD_DB="$evidence_directory/task_board.db" PYTHONPATH="$repo/examples/task_board:$repo/src" python "$repo/examples/task_board/python-app-console/app/main.py"
PYTHONPATH="$repo/src" python -m unittest discover -s "$repo/examples/task_board/python-app-console/app" -p 'test_task_board.py' -v
bash "$repo/examples/trace-chain/verify.sh"
bash "$repo/examples/facet-trace/verify.sh"
bash "$repo/examples/trace-chain/verify-standard-telemetry.sh"
bash "$repo/examples/trace-chain/verify-standard-order.sh"
bash "$repo/examples/trace-chain/verify-standard-graph.sh"
bash "$repo/examples/trace-chain/verify-standard-stream.sh"
echo "PASS: all Python examples"
