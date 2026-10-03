#!/usr/bin/env bash
set -euo pipefail
example="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$example/../.." && pwd)"
if [[ -z "${TEAQL_TRACE_CHAIN_DB:-}" ]]; then
  trace_test_directory="$(mktemp -d)"
  export TEAQL_TRACE_CHAIN_DB="$trace_test_directory/trace-chain.sqlite"
fi
if [[ -z "${TEAQL_TRACE_CHAIN_SHARED_DB:-}" ]]; then
  ownership_directory="$(mktemp -d -t teaql-python-shared.XXXXXX)"
  export TEAQL_TRACE_CHAIN_SHARED_DB="$ownership_directory/shared.sqlite"
fi
if [[ -z "${TEAQL_TRACE_CHAIN_PAGE_STREAM_DB:-}" ]]; then
  page_stream_directory="$(mktemp -d -t teaql-python-page-stream.XXXXXX)"
  export TEAQL_TRACE_CHAIN_PAGE_STREAM_DB="$page_stream_directory/page-stream.sqlite"
fi
if [[ "$TEAQL_TRACE_CHAIN_PAGE_STREAM_DB" == "$TEAQL_TRACE_CHAIN_DB" || "$TEAQL_TRACE_CHAIN_PAGE_STREAM_DB" == "$TEAQL_TRACE_CHAIN_SHARED_DB" ]]; then
  echo 'FAIL: page/stream requires its own retained database' >&2
  exit 1
fi
if [[ "$TEAQL_TRACE_CHAIN_SHARED_DB" == "$TEAQL_TRACE_CHAIN_DB" ]]; then
  echo 'FAIL: normative and ownership fixtures require separate databases' >&2
  exit 1
fi
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$example/lib:$repo/src${PYTHONPATH:+:$PYTHONPATH}"
snapshot="$(mktemp)"
(cd "$example/lib" && rg --files --hidden -g '!**/__pycache__/**' | LC_ALL=C sort | xargs -d '\n' sha256sum) > "$snapshot"
for attempt in first second; do
  echo "Run $attempt on $TEAQL_TRACE_CHAIN_DB without cleanup"
  python "$example/main.py"
  echo "Mutation privacy $attempt on $TEAQL_TRACE_CHAIN_DB without cleanup"
  python "$example/mutation_privacy.py"
  echo "Ownership $attempt on $TEAQL_TRACE_CHAIN_SHARED_DB without cleanup"
  run_log="$(mktemp -t teaql-python-shared.XXXXXX.log)"
  env -u TEAQL_TRACE_CHAIN_SCENARIO TEAQL_TRACE_CHAIN_DB="$TEAQL_TRACE_CHAIN_SHARED_DB" \
    python "$example/shared_reference.py" | tee "$run_log"
  rg -Fq 'PASS: Python shared ownership 4 scenarios' "$run_log"
  echo "Page/stream $attempt on $TEAQL_TRACE_CHAIN_PAGE_STREAM_DB without cleanup"
  python "$example/page_stream.py"
done
(cd "$example/lib" && sha256sum --check "$snapshot")
echo "PASS: two runs on the same database; generated library hashes unchanged"
