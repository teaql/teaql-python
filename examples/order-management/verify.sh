#!/usr/bin/env bash
set -euo pipefail
example="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$example/../.." && pwd)"
app="$example/python-app-console"
python="${PYTHON:-python}"
if [[ -n "${TEAQL_ORDER_EVIDENCE_DIR:-}" ]]; then
  evidence="$TEAQL_ORDER_EVIDENCE_DIR"
  mkdir "$evidence"
else
  evidence="$(mktemp -d -t teaql-python-order-evidence.XXXXXXXX)"
fi
scratch="$(mktemp -d -t teaql-python-order-scratch.XXXXXXXX)"
trap 'status=$?; trap - EXIT; rm -rf -- "$scratch"; exit "$status"' EXIT
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$example/python-lib-core:$app:$repo/src"
fingerprint() {
  (cd "$example" && find python-lib-core python-app-console -type f \
    ! -path '*/__pycache__/*' ! -path '*/.local/*' -print0 | sort -z | xargs -0 sha256sum)
}
fingerprint > "$evidence/source-before.sha256"
"$python" - "$repo" "$example/python-lib-core" <<'PY' > "$evidence/origins.log"
from pathlib import Path
import sys, teaql, Q
runtime, library = map(Path, sys.argv[1:])
assert Path(teaql.__file__).resolve() == (runtime / 'src/teaql/__init__.py').resolve()
assert Path(Q.__file__).resolve() == (library / 'Q.py').resolve()
print('Runtime: ' + teaql.__file__)
print('Domain library: ' + Q.__file__)
PY
"$python" "$repo/scripts/verify_generated_runtime_boundary.py" "$example" > "$evidence/runtime-boundary.log"
"$python" -m unittest discover -s "$example" -p 'test_sql_log_intent.py' -v > "$evidence/original-tests.log" 2>&1
cd "$app"
for round in 1 2; do
  TEAQL_ORDER_MANAGEMENT_DB="$evidence/order.sqlite" \
    "$python" -m app.main > "$evidence/run-$round.log" 2>&1
done
fingerprint > "$evidence/source-after.sha256"
cmp "$evidence/source-before.sha256" "$evidence/source-after.sha256"
"$python" - "$evidence" <<'PY'
import datetime, decimal, hashlib, json, pathlib, sqlite3, sys
root = pathlib.Path(sys.argv[1])
test = (root / 'original-tests.log').read_text()
assert 'test_generated_queries_retain_intent_at_sql_sink' in test and '\nOK\n' in test
for round in [1, 2]:
    text = (root / f'run-{round}.log').read_text()
    assert '[query] matched 1 order(s)' in text and 'WEB-2026-001  2026-08-12  129.95' in text
    expected = '[seed] inserted deterministic platform, customer, status, and order' if round == 1 else 'no duplicate rows added'
    assert expected in text
database = root / 'order.sqlite'
with sqlite3.connect(database.resolve().as_uri() + '?mode=ro&immutable=1', uri=True) as connection:
    rows = connection.execute('SELECT order_number,order_date,total_amount,version FROM customer_order_data').fetchall()
    assert len(rows) == 1 and rows[0][0] == 'WEB-2026-001', rows
    assert datetime.date.fromisoformat(str(rows[0][1])[:10]) == datetime.date(2026, 8, 12)
    assert decimal.Decimal(str(rows[0][2])) == decimal.Decimal('129.95') and rows[0][3] == 1
    presets = connection.execute('SELECT request_id,version FROM order_search_preset_data').fetchall()
    assert presets == [('quick-start-pending-orders', 1)], presets
    assert connection.execute('SELECT count(*) FROM customer_data').fetchone() == (1,)
    assert connection.execute('PRAGMA quick_check').fetchone() == ('ok',)
receipt = dict(schema='teaql.python-order-business/v1', passed=True,
    sameTerminalDatabase=True, terminalRuns=2, nativeWorkspaceEntryUsed=True,
    originalIntentPrivacyRegressionPassed=True, namedSiblingDomainLibraryConsumed=True,
    currentRuntimeSourceVerified=True, generatedScopesUnchanged=True, orders=rows, presets=presets,
    databaseSHA256=hashlib.sha256(database.read_bytes()).hexdigest())
(root / 'business-receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
print(json.dumps(dict(passed=True, terminalRuns=2, originalIntentPrivacyRegressionPassed=True)))
PY
