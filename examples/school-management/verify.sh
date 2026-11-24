#!/usr/bin/env bash
set -euo pipefail
example="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$example/../.." && pwd)"
app="$example/python-app-console"
python="${PYTHON:-python}"
if [[ -n "${TEAQL_SCHOOL_EVIDENCE_DIR:-}" ]]; then
  evidence="$TEAQL_SCHOOL_EVIDENCE_DIR"
  mkdir "$evidence"
else
  evidence="$(mktemp -d -t teaql-python-school-evidence.XXXXXXXX)"
fi
scratch="$(mktemp -d -t teaql-python-school-scratch.XXXXXXXX)"
trap 'status=$?; trap - EXIT; rm -rf -- "$scratch"; exit "$status"' EXIT
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$app:$example/python-lib-core:$repo/src"
export TEAQL_SCHOOL_MANAGEMENT_DB="$evidence/showcase.sqlite"
fingerprint() {
  (cd "$example" && find python-lib-core python-app-console -type f \
    ! -path '*/__pycache__/*' ! -path '*/.local/*' -print0 | sort -z | xargs -0 sha256sum)
}
fingerprint > "$evidence/source-before.sha256"
"$python" - "$repo" "$example/python-lib-core" <<'PY' > "$evidence/runtime-origin.log"
from pathlib import Path
import sys, teaql, Q
expected = Path(sys.argv[1]) / 'src/teaql/__init__.py'
assert Path(teaql.__file__).resolve() == expected.resolve(), teaql.__file__
domain = Path(sys.argv[2]) / 'Q.py'
assert Path(Q.__file__).resolve() == domain.resolve(), Q.__file__
print('Current source runtime: ' + str(expected))
print('Generated domain Q: ' + str(domain))
PY
"$python" "$repo/scripts/verify_generated_runtime_boundary.py" "$example" > "$evidence/runtime-boundary.log"
"$python" -m app.main > "$evidence/application.log" 2>&1
sha256sum "$TEAQL_SCHOOL_MANAGEMENT_DB" > "$evidence/database-before-rejection.sha256"
set +e
"$python" -m app.main > "$evidence/existing-database-rejected.log" 2>&1
rejected=$?
set -e
[[ "$rejected" == 1 ]]
rg -Fq 'existing data is preserved' "$evidence/existing-database-rejected.log"
sha256sum "$TEAQL_SCHOOL_MANAGEMENT_DB" > "$evidence/database-after-rejection.sha256"
cmp "$evidence/database-before-rejection.sha256" "$evidence/database-after-rejection.sha256"
"$python" -m pytest "$app/tests" -q --basetemp "$scratch/pytest" \
  -o "cache_dir=$scratch/pytest-cache" > "$evidence/bootstrap-tests.log" 2>&1
"$python" -m unittest discover -s "$app" -p 'test_sql_log_intent.py' -v > "$evidence/sql-log-intent.log" 2>&1
TEAQL_SCHOOL_BOOTSTRAP_EVIDENCE_DIR="$evidence/bootstrap" \
  bash "$repo/scripts/verify-school-bootstrap-example.sh" > "$evidence/bootstrap.log" 2>&1
fingerprint > "$evidence/source-after.sha256"
cmp "$evidence/source-before.sha256" "$evidence/source-after.sha256"
"$python" - "$evidence" <<'PY'
import hashlib, json, pathlib, sqlite3, sys
root = pathlib.Path(sys.argv[1])
assert 'PASS Python School Management: bootstrap, portable Query parity, and forward relations' in (root / 'application.log').read_text()
assert '1 passed' in (root / 'bootstrap-tests.log').read_text()
assert 'test_generated_queries_retain_intent_at_sql_sink' in (root / 'sql-log-intent.log').read_text()
assert '\nOK\n' in (root / 'sql-log-intent.log').read_text()
for logging in ['on', 'off']:
    for round in [1, 2]:
        expected = f'PASS Python generated bootstrap trace logging={logging == "on"} fresh={round == 1} originalVersion={1 if round == 1 else 3}'
        assert expected in (root / 'bootstrap' / f'{logging}-{round}.log').read_text()
database = root / 'showcase.sqlite'
with sqlite3.connect(database.resolve().as_uri() + '?mode=ro&immutable=1', uri=True) as connection:
    rows = connection.execute('SELECT name,version,student_capacity FROM school_data').fetchall()
    assert rows == [('Riverside Primary School', 1, 800)], rows
    assert connection.execute('PRAGMA quick_check').fetchone() == ('ok',)
receipt = dict(schema='teaql.python-school-business/v1', passed=True,
    originalApplicationAssertionsPassed=True, bootstrapConcurrencyTestPassed=True,
    sqlLogIntentTestPassed=True, bootstrapRoundsPerMode=2, loggingModes=['on', 'off'],
    sameBootstrapDatabases=True, preexistingDatabaseRejectedWithoutModification=True,
    generatedScopesUnchanged=True, sqliteRows=rows,
    databaseSHA256=hashlib.sha256(database.read_bytes()).hexdigest())
(root / 'business-receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
print(json.dumps(dict(passed=True, sameBootstrapDatabases=True, existingDatabasePreserved=True)))
PY
