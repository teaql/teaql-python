#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 1 || -e "$1" ]]; then
  echo 'Usage: bash verify-empty.sh <new-sqlite-path>; the two-round evidence database is retained.' >&2
  exit 2
fi
example_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$example_dir/../.." && pwd)"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$example_dir/generated:$repo/src"
export TEAQL_EMPTY_DB="$1"
export TEAQL_EMPTY_VECTORS="$example_dir/empty-aggregate-vectors.json"
python - "$example_dir" "$repo" <<'PY'
import hashlib
import json
import pathlib
import sys
import teaql
example, repo = map(pathlib.Path, sys.argv[1:])
assert pathlib.Path(teaql.__file__).resolve().is_relative_to(repo / "src")
manifest = json.loads((example / "fixture-manifest.json").read_text())
assert hashlib.sha256((example / "model.xml").read_bytes()).hexdigest() == manifest["modelSha256"]
for relative, expected in manifest["files"].items():
    assert hashlib.sha256((example / "generated" / relative).read_bytes()).hexdigest() == expected, relative
assert hashlib.sha256((example / "empty-aggregate-vectors.json").read_bytes()).hexdigest() == \
    "cfaa8dec196bbfa85e830fd0d67f321b17875b6f7d7c5f7cd28e0f2f6770ced0"
print("PASS immutable generated empty-query fixture, shared vectors and repository-local runtime")
PY
for round in 1 2; do
  TEAQL_EMPTY_ROUND="$round" python -B "$example_dir/empty_aggregates.py"
done
echo "PASS Python generated empty aggregates twice on $TEAQL_EMPTY_DB"
