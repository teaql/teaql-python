#!/usr/bin/env bash
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
expected=(business-clock business-id conformance expression-profiles facet-trace fix-e-alignment internal-id mutation-policy object-storage opaque-entity-reference order-management query-policy scalar-type-probe school-management task_board trace-chain typed-extension-spi)
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
export TEAQL_SCHOOL_MANAGEMENT_DB="$evidence_directory/school.sqlite"
export TEAQL_SCALAR_PROBE_DB="$evidence_directory/scalar.sqlite"
export TEAQL_FIX_E_EVIDENCE_DIR="$evidence_directory/fix-e"
echo "Retained compact Python example inventory evidence: $evidence_directory"

mapfile -t embedded_runtime_dirs < <(find "$repo/examples" -type d -name teaql -print)
if ((${#embedded_runtime_dirs[@]})); then
  printf 'generated examples must depend on the packaged runtime; embedded teaql snapshot: %s\n' \
    "${embedded_runtime_dirs[@]}" >&2
  exit 1
fi
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
TEAQL_GENERATED_E_PROFILE_EVIDENCE_DIR="$evidence_directory/expression-profiles" \
  python "$repo/examples/expression-profiles/verify-local.py"
PYTHONPATH="$repo/examples/conformance:$repo/src" python -m app.main
PYTHONPATH="$repo/src" python -m unittest discover -s "$repo/examples/conformance" -p 'test_sql_log_intent.py' -v
PYTHONPATH="$repo/examples/school-management:$repo/src" python -m app.main
bash "$repo/scripts/verify-school-bootstrap-example.sh"
PYTHONPATH="$repo/src" python -m unittest discover -s "$repo/examples/school-management" -p 'test_sql_log_intent.py' -v
PYTHONPATH="$repo/src" python "$repo/examples/mutation-policy/main.py"
PYTHONPATH="$repo/src" python "$repo/examples/business-clock/main.py"
PYTHONPATH="$repo/src" python "$repo/examples/business-id/main.py"
PYTHONPATH="$repo/src" python "$repo/examples/internal-id/main.py"
PYTHONPATH="$repo/src" python "$repo/examples/typed-extension-spi/main.py"
PYTHONPATH="$repo/src" python "$repo/examples/query-policy/main.py"
PYTHONPATH="$repo/src" python "$repo/examples/opaque-entity-reference/main.py"
TEAQL_ORDER_MANAGEMENT_DB="$evidence_directory/order.db" \
  PYTHONPATH="$repo/examples/order-management/python-lib-core:$repo/src" \
  python "$repo/examples/order-management/python-app-console/app.py"
PYTHONPATH="$repo/src" python -m unittest discover -s "$repo/examples/order-management" -p 'test_sql_log_intent.py' -v
TEAQL_TASK_BOARD_DB="$evidence_directory/task_board.db" PYTHONPATH="$repo/examples/task_board:$repo/src" python "$repo/examples/task_board/main.py"
PYTHONPATH="$repo/src" python -m unittest discover -s "$repo/examples/task_board" -p 'test_task_board.py' -v
bash "$repo/examples/trace-chain/verify.sh"
bash "$repo/examples/facet-trace/verify.sh"
bash "$repo/examples/trace-chain/verify-standard-telemetry.sh"
bash "$repo/examples/trace-chain/verify-standard-order.sh"
bash "$repo/examples/trace-chain/verify-standard-graph.sh"
bash "$repo/examples/trace-chain/verify-standard-stream.sh"
echo "PASS: all Python examples"
