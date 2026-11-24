#!/usr/bin/env bash
set -euo pipefail
example="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$example/../.." && pwd)"
if [[ -n "${TEAQL_CONFORMANCE_EVIDENCE_DIR:-}" ]]; then
 evidence="$TEAQL_CONFORMANCE_EVIDENCE_DIR"
 mkdir "$evidence"
else
 evidence="$(mktemp -d -t teaql-work-item-evidence.XXXXXXXX)"
fi
unset TEAQL_ALLOW_SENSITIVE_PLAINTEXT_LOGS
app="$example/python-app-console"
python="${PYTHON:-python}"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$example/python-lib-core:$app:$repo/src"
fingerprint() {
 (cd "$example" && find python-lib-core python-app-console -type f ! -path '*/__pycache__/*' ! -path '*/.local/*' -print0 | sort -z | xargs -0 sha256sum)
}
fingerprint > "$evidence/source-before.sha256"
"$python" - "$example" "$repo" <<'CHECK' > "$evidence/origins.json"
import json,pathlib,sys,teaql,Q
example,repo=map(pathlib.Path,sys.argv[1:])
assert pathlib.Path(teaql.__file__).resolve()==(repo/'src/teaql/__init__.py').resolve()
assert pathlib.Path(Q.__file__).resolve()==(example/'python-lib-core/Q.py').resolve()
print(json.dumps(dict(runtime=teaql.__file__,domain=Q.__file__),indent=2))
CHECK
"$python" "$repo/scripts/verify_generated_runtime_boundary.py" "$example" > "$evidence/runtime-boundary.log"
for round in 1 2; do
 TEAQL_CONFORMANCE_DB="$evidence/smoke-$round.sqlite" "$python" -m app.main > "$evidence/smoke-$round.log" 2>&1
 rg -Fq 'PASS Python minimum runtime conformance: 8/8' "$evidence/smoke-$round.log"
done
sha256sum "$evidence/smoke-1.sqlite" > "$evidence/before-rejection.sha256"
set +e
TEAQL_CONFORMANCE_DB="$evidence/smoke-1.sqlite" "$python" -m app.main > "$evidence/existing-database-rejected.log" 2>&1
rejected=$?
set -e
[[ "$rejected" == 1 ]]
rg -Fq 'existing data is preserved' "$evidence/existing-database-rejected.log"
sha256sum "$evidence/smoke-1.sqlite" > "$evidence/after-rejection.sha256"
cmp "$evidence/before-rejection.sha256" "$evidence/after-rejection.sha256"
"$python" "$app/app/managed_creation.py" > "$evidence/managed-creation.log" 2>&1
TEAQL_MANAGED_CREATION_DB="$evidence/managed.sqlite" "$python" "$app/app/managed_sqlite.py" > "$evidence/managed-sqlite.log" 2>&1
"$python" -m unittest discover -s "$app" -p 'test_sql_log_intent.py' -v > "$evidence/sql-log-intent.log" 2>&1
fingerprint > "$evidence/source-after.sha256"
cmp "$evidence/source-before.sha256" "$evidence/source-after.sha256"
"$python" - "$evidence" <<'CHECK'
import hashlib,json,pathlib,sqlite3,sys
root=pathlib.Path(sys.argv[1]);databases=[]
for round in [1,2]:
 database=root/f'smoke-{round}.sqlite'
 with sqlite3.connect(database.resolve().as_uri()+'?mode=ro&immutable=1',uri=True) as connection:
  rows=connection.execute('SELECT title,version FROM work_item_data').fetchall()
  assert len(rows)==1 and rows[0][1]==-3,rows
  assert connection.execute('SELECT count(*) FROM platform_data').fetchone()==(1,)
  assert connection.execute('PRAGMA quick_check').fetchone()==('ok',)
 databases.append(dict(round=round,workItems=rows,sha256=hashlib.sha256(database.read_bytes()).hexdigest()))
managed={}
for name,prefix in [('managed-creation','PYTHON_MANAGED_CREATION='),('managed-sqlite','PYTHON_MANAGED_SQLITE=')]:
 lines=[line.removeprefix(prefix) for line in (root/(name+'.log')).read_text().splitlines() if line.startswith(prefix)]
 assert len(lines)==1,name
 result=json.loads(lines[0]);assert len(result['rounds'])==2,result;managed[name]=result
assert '\nOK\n' in (root/'sql-log-intent.log').read_text()
receipt=dict(schema='teaql.python-work-item-business/v1',passed=True,smokeRuns=2,smokeDatabasesFreshAndRetained=True,
 managedRoundsUseSameDatabase=True,originalBusinessAssertionsRetained=True,preexistingSmokeDatabaseRejectedWithoutModification=True,
 generatedScopesUnchanged=True,nativeWorkspaceEntryUsed=True,smokeResults=databases,managed=managed,
 origins=json.loads((root/'origins.json').read_text()),managedDatabaseSHA256=hashlib.sha256((root/'managed.sqlite').read_bytes()).hexdigest())
(root/'business-receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(passed=True,smokeRuns=2,managedSameDatabaseRounds=2)))
CHECK
