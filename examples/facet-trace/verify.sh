#!/usr/bin/env bash
set -euo pipefail
example="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$example/../.." && pwd)"
facet_run_directory="$(mktemp -d -t teaql-python-facet.XXXXXX)"
export TEAQL_FACET_TRACE_DB="$facet_run_directory/school.sqlite"
export PYTHONDONTWRITEBYTECODE=1
# Runtime examples always exercise this repository, never an installed release.
export PYTHONPATH="$example/lib:$repo/src"
unset TEAQL_ALLOW_SENSITIVE_PLAINTEXT_LOGS
(cd "$example/lib" && rg --files --hidden -g '!**/__pycache__/**' | LC_ALL=C sort | xargs -d '\n' sha256sum) > "$facet_run_directory/library-before.sha256"
for round in first second; do
  log="$facet_run_directory/$round.log"
  if ! timeout --kill-after=5s 60s python -B "$example/main.py" > "$log" 2>&1; then
    tail -80 "$log" >&2
    echo "FAIL: generated Facet $round; retained evidence $facet_run_directory" >&2
    exit 1
  fi
  [[ "$(rg -c '^FACET_OBSERVED ' "$log")" == 20 ]]
  rg -Fxq 'PASS: Python generated Facets; 20 root/nested/loaded/empty/includeAll/logging scenarios; Q/E/save; retained SQLite' "$log"
  echo "PASS: generated Facet $round, 20 scenarios; same database $TEAQL_FACET_TRACE_DB; log $log"
done
(cd "$example/lib" && sha256sum --check "$facet_run_directory/library-before.sha256")
echo "PASS: generated Facet library unchanged; retained evidence $facet_run_directory"
