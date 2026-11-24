#!/usr/bin/env bash
set -euo pipefail
example="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$example/../.." && pwd)"
if [[ -n "${TEAQL_FACET_EVIDENCE_DIR:-}" ]]; then
  evidence="$TEAQL_FACET_EVIDENCE_DIR"
  mkdir "$evidence"
else
  evidence="$(mktemp -d -t teaql-facet-evidence.XXXXXXXX)"
fi
export TEAQL_FACET_TRACE_DB="$evidence/school.sqlite"
unset TEAQL_ALLOW_SENSITIVE_PLAINTEXT_LOGS
app="$example/python-app-console"
python="${PYTHON:-python}"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$example/python-lib-core:$repo/src"
fingerprint() {
  (cd "$example" && find python-lib-core python-app-console -type f ! -path '*/__pycache__/*' -print0 | sort -z | xargs -0 sha256sum)
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
  timeout --kill-after=5s 120s "$python" -B "$app/app/main.py" > "$evidence/run-$round.log" 2>&1
  [[ "$(rg -c '^FACET_OBSERVED ' "$evidence/run-$round.log")" == 20 ]]
  rg -Fxq 'PASS: Python generated Facets; 20 root/nested/loaded/empty/includeAll/logging scenarios; Q/E/save; retained SQLite' "$evidence/run-$round.log"
done
fingerprint > "$evidence/source-after.sha256"
cmp "$evidence/source-before.sha256" "$evidence/source-after.sha256"
"$python" - "$evidence" <<'CHECK'
import hashlib,json,pathlib,sqlite3,sys
root=pathlib.Path(sys.argv[1]);database=root/'school.sqlite'
with sqlite3.connect(database.resolve().as_uri()+'?mode=ro&immutable=1',uri=True) as connection:
 rows=connection.execute('SELECT name,version FROM school_data ORDER BY name').fetchall()
 assert rows==[('FACET-PRIVATE-SCHOOL',1),('FACET-PRIVATE-SCHOOL-B',1)],rows
 assert connection.execute('SELECT count(*) FROM platform_data').fetchone()==(1,)
 assert connection.execute('SELECT count(*) FROM school_type_data').fetchone()==(2,)
 assert connection.execute('PRAGMA quick_check').fetchone()==('ok',)
receipt=dict(schema='teaql.python-facet-business/v1',passed=True,scenariosPerRun=20,runs=2,sameDatabase=True,
 generatedScopesUnchanged=True,originalBusinessProgramByteExact=True,nativeWorkspaceEntryUsed=True,
 origins=json.loads((root/'origins.json').read_text()),schools=rows,databaseSHA256=hashlib.sha256(database.read_bytes()).hexdigest())
(root/'business-receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(passed=True,scenariosPerRun=20,runs=2)))
CHECK
