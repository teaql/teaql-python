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
if [[ -z "${TEAQL_TRACE_CHAIN_AGGREGATE_DB:-}" ]]; then
  aggregate_directory="$(mktemp -d -t teaql-python-aggregate.XXXXXX)"
  export TEAQL_TRACE_CHAIN_AGGREGATE_DB="$aggregate_directory/aggregate.sqlite"
fi
for other_db in "$TEAQL_TRACE_CHAIN_DB" "$TEAQL_TRACE_CHAIN_SHARED_DB" "$TEAQL_TRACE_CHAIN_PAGE_STREAM_DB"; do
  if [[ "$TEAQL_TRACE_CHAIN_AGGREGATE_DB" == "$other_db" ]]; then
    echo 'FAIL: aggregate fixture requires its own retained database' >&2
    exit 1
  fi
done
if [[ -z "${TEAQL_TRACE_CHAIN_CHECKER_DB:-}" ]]; then
  checker_directory="$(mktemp -d -t teaql-python-checker.XXXXXX)"
  export TEAQL_TRACE_CHAIN_CHECKER_DB="$checker_directory/checker.sqlite"
fi
for other_db in "$TEAQL_TRACE_CHAIN_DB" "$TEAQL_TRACE_CHAIN_SHARED_DB" "$TEAQL_TRACE_CHAIN_PAGE_STREAM_DB" "$TEAQL_TRACE_CHAIN_AGGREGATE_DB"; do
  if [[ "$TEAQL_TRACE_CHAIN_CHECKER_DB" == "$other_db" ]]; then
    echo 'FAIL: Checker overlap fixture requires its own retained database' >&2
    exit 1
  fi
done
export PYTHONPATH="$example/lib:$repo/src${PYTHONPATH:+:$PYTHONPATH}"
snapshot="$(mktemp)"
(cd "$example/lib" && rg --files --hidden -g '!**/__pycache__/**' | LC_ALL=C sort | xargs -d '\n' sha256sum) > "$snapshot"
echo "Generated library manifest: $snapshot"
for attempt in first second; do
  intent_log="$(mktemp -t teaql-python-intent.XXXXXX.log)"
  if ! python -m pytest -q "$repo/tests/provider/sqlite/test_trace_chain.py" \
    -k 'request_intent_matrix or graph_intent_gate or explicit_mutation_comment_survives_blank_route' \
    -s > "$intent_log" 2>&1; then
    sed -n '1,200p' "$intent_log" >&2
    echo "FAIL: native request intent gate; evidence $intent_log" >&2
    exit 1
  fi
  rg -Fq 'INTENT_GATE_PASS' "$intent_log"
  rg -Fq 'INTENT_TAIL_PASS' "$intent_log"
  echo "PASS: native intent matrix $attempt; evidence $intent_log"
  like_log="$(mktemp -t teaql-python-like.XXXXXX.log)"
  if ! python -m pytest -q -p no:cacheprovider "$repo/tests/provider/sqlite/test_like_intent.py" \
    > "$like_log" 2>&1; then
    sed -n '1,200p' "$like_log" >&2
    echo "FAIL: native LIKE intent privacy; evidence $like_log" >&2
    exit 1
  fi
  rg -q '^66 passed in ' "$like_log"
  echo "PASS: native LIKE privacy $attempt; evidence $like_log"
  echo "Run $attempt on $TEAQL_TRACE_CHAIN_DB without cleanup"
  main_log="$(mktemp -t teaql-python-main.XXXXXX.log)"
  timeout --kill-after=5s 60s python "$example/main.py" | tee "$main_log"
  rg -Fxq 'PASS: identity controls reject duplicate, missing and equal-ID type collapse' "$main_log"
  [[ "$(rg -c '^GRAPH IDENTITY EVIDENCE ' "$main_log")" == 1 ]]
  [[ "$(rg -c '^BOOTSTRAP INTENT EVIDENCE ' "$main_log")" == 2 ]]
  rg -Fxq 'PASS: generated library unchanged; all trace example checks passed' "$main_log"
  echo "Mutation privacy $attempt on $TEAQL_TRACE_CHAIN_DB without cleanup"
  privacy_log="$(mktemp -t teaql-python-privacy.XXXXXX.log)"
  python "$example/mutation_privacy.py" | tee "$privacy_log"
  rg -Fq 'PASS: Python generated loaded delete privacy; 2 writes/2 reads/2 audits; independent next request' "$privacy_log"
  rg -Fq 'PASS: Python generated unchanged scalar privacy; 1 write/1 read/1 audit' "$privacy_log"
  echo "Assigned identities $attempt on $TEAQL_TRACE_CHAIN_SHARED_DB without cleanup"
  assigned_log="$(mktemp -t teaql-python-assigned.XXXXXX.log)"
  TEAQL_TRACE_CHAIN_DB="$TEAQL_TRACE_CHAIN_SHARED_DB" \
    timeout --kill-after=5s 60s python "$example/assigned_identity.py" | tee "$assigned_log"
  rg -Fxq 'PASS: Python generated assigned identity 2 scenarios; command/SQL/audit and independent reload' "$assigned_log"
  echo "Ownership $attempt on $TEAQL_TRACE_CHAIN_SHARED_DB without cleanup"
  run_log="$(mktemp -t teaql-python-shared.XXXXXX.log)"
  env -u TEAQL_TRACE_CHAIN_SCENARIO TEAQL_TRACE_CHAIN_DB="$TEAQL_TRACE_CHAIN_SHARED_DB" \
    python "$example/shared_reference.py" | tee "$run_log"
  rg -Fq 'PASS: Python shared ownership 4 scenarios' "$run_log"
  echo "Page/stream $attempt on $TEAQL_TRACE_CHAIN_PAGE_STREAM_DB without cleanup"
  python "$example/page_stream.py"
  echo "Aggregate $attempt on $TEAQL_TRACE_CHAIN_AGGREGATE_DB without cleanup"
  aggregate_log="$(mktemp -t teaql-python-aggregate.XXXXXX.log)"
  python "$example/relation_aggregate.py" | tee "$aggregate_log"
  rg -Fq 'FORWARD_NOTLOADED_OBSERVED {"logging": true' "$aggregate_log"
  rg -Fq 'FORWARD_NOTLOADED_OBSERVED {"logging": false' "$aggregate_log"
  echo "Checker overlap $attempt on $TEAQL_TRACE_CHAIN_CHECKER_DB without cleanup"
  checker_log="$(mktemp -t teaql-python-checker.XXXXXX.log)"
  TEAQL_TRACE_CHAIN_DB="$TEAQL_TRACE_CHAIN_CHECKER_DB" \
    python "$example/checker_overlap.py" | tee "$checker_log"
  rg -Fq 'PASS: Python generated Checker overlap 4 scenarios; accepted-only command/SQL/audit; serialized callbacks' "$checker_log"
  echo "PASS: generated Checker overlap $attempt; evidence $checker_log"
done
(cd "$example/lib" && sha256sum --check "$snapshot")
echo "PASS: two runs on the same database; generated library hashes unchanged"
