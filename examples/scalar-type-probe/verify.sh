#!/usr/bin/env bash
set -euo pipefail

example_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$example_dir/../.." && pwd)"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$example_dir/generated:$repo/src"

verify_fixture() {
  python - "$example_dir" "$repo" <<'PY'
import hashlib
import json
import pathlib
import sys
import teaql

example, repo = map(pathlib.Path, sys.argv[1:])
assert pathlib.Path(teaql.__file__).resolve().is_relative_to(repo / "src"), "example must use this repository's runtime"
manifest = json.loads((example / "fixture-manifest.json").read_text())
assert hashlib.sha256((example / "model.xml").read_bytes()).hexdigest() == manifest["modelSha256"]
actual = sorted(str(path.relative_to(example / "generated"))
                for path in (example / "generated").rglob("*") if path.is_file() and path.suffix != ".pyc")
assert actual == sorted(manifest["files"]), "generated fixture inventory changed"
for relative, expected in manifest["files"].items():
    assert hashlib.sha256((example / "generated" / relative).read_bytes()).hexdigest() == expected, relative
print("PASS fixed generated scalar fixture and local runtime provenance")
PY
}

verify_fixture
if [[ -z "${TEAQL_SCALAR_PROBE_DB:-}" ]]; then
  scalar_run_dir="$(mktemp -d -t teaql-python-scalar.XXXXXXXX)"
  export TEAQL_SCALAR_PROBE_DB="$scalar_run_dir/scalar.sqlite"
fi
for round in 1 2; do
  python "$example_dir/main.py"
done
verify_fixture
echo "PASS Python generated scalar fixture twice on $TEAQL_SCALAR_PROBE_DB"
