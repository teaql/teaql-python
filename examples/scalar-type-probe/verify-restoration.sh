#!/usr/bin/env bash
set -euo pipefail
example_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$example_dir/../.." && pwd)"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$example_dir/generated:$repo/src"
if [[ $# -gt 1 ]]; then exit 2; fi
if [[ $# -eq 1 ]]; then
  export TEAQL_SCALAR_PROBE_DB="$1"
elif [[ -z "${TEAQL_SCALAR_PROBE_DB:-}" ]]; then
  evidence_dir="$(mktemp -d -t teaql-python-restoration-evidence.XXXXXXXX)"
  export TEAQL_SCALAR_PROBE_DB="$evidence_dir/restoration.sqlite"
fi
verify_fixture() {
  python - "$example_dir" <<'PY'
import hashlib
import json
import pathlib
import sys
example = pathlib.Path(sys.argv[1])
manifest = json.loads((example / "fixture-manifest.json").read_text())
assert hashlib.sha256((example / "model.xml").read_bytes()).hexdigest() == manifest["modelSha256"]
for relative, expected in manifest["files"].items():
    assert hashlib.sha256((example / "generated" / relative).read_bytes()).hexdigest() == expected, relative
print("PASS immutable generated restoration fixture")
PY
}
verify_fixture
for round in 1 2; do
  TEAQL_PROBE_ROUND="$round" python -B "$example_dir/restore_probe.py"
done
verify_fixture
echo "PASS Python known-baseline restoration twice on $TEAQL_SCALAR_PROBE_DB"
