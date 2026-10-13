#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
evidence="$(mktemp -d -t teaql-python-standard-stream.XXXXXXXX)"
cd "$repo"
export PYTHONPATH="$repo/examples/trace-chain/lib:$repo/src"
export PYTHONDONTWRITEBYTECODE=1
export TEAQL_STANDARD_STREAM_DB="$evidence/stream.sqlite"
fingerprint() { find examples/trace-chain/lib -type f -not -path '*/__pycache__/*' -print0 | sort -z | xargs -0 sha256sum; }
fingerprint > "$evidence/library-before.sha256"
for round in 1 2; do
  python examples/trace-chain/standard_stream.py > "$evidence/run-$round.log" 2>&1
  rg -q '^PYTHON_STANDARD_STREAM PASSED complete=3 early_close=1 independent=1 ordinary_sql_logs=0$' "$evidence/run-$round.log"
  cat "$evidence/run-$round.log"
done
fingerprint > "$evidence/library-after.sha256"
cmp "$evidence/library-before.sha256" "$evidence/library-after.sha256"
echo "PASS: Python standard stream twice on retained SQLite; generated library unchanged; evidence=$evidence"
