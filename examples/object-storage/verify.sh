#!/usr/bin/env bash
set -euo pipefail
example="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$example/../.." && pwd)"
: "${TEAQL_S3_ENDPOINT:?dedicated local test endpoint required}"
: "${TEAQL_S3_BUCKET:?dedicated test bucket required}"
: "${TEAQL_S3_ACCESS_KEY:?test access key required}"
: "${TEAQL_S3_SECRET_KEY:?test secret key required}"
app="$example/python-app-console"
library="$example/python-lib-core"
python="${PYTHON:-python3}"
if [[ -n "${TEAQL_ORDER_ATTACHMENT_EVIDENCE_DIR:-}" ]]; then
  evidence="$TEAQL_ORDER_ATTACHMENT_EVIDENCE_DIR"
  mkdir -p "$(dirname "$evidence")"
  mkdir "$evidence"
else
  evidence="$(mktemp -d -t teaql-python-order-attachment.XXXXXXXX)"
fi
evidence="$(cd "$evidence" && pwd)"
export PYTHONPATH="$library:$app:$repo/src"
export PYTHONDONTWRITEBYTECODE=1
fingerprint() {
  (cd "$example" && find python-lib-core python-app-console -type f -name '*.py' -print0 | sort -z | xargs -0 sha256sum)
}
fingerprint > "$evidence/source-before.sha256"
cd "$repo"
"$python" -m pytest -p no:cacheprovider tests/runtime/test_object_storage.py -q | tee "$evidence/provider-tests.log"
"$python" -m app.s3_lifecycle | tee "$evidence/s3-calibration.log"
"$python" - "$library" "$repo" <<'PY' > "$evidence/origins.log"
from pathlib import Path
import sys, Q, teaql
library, runtime = map(Path, sys.argv[1:])
assert Path(Q.__file__).resolve() == library / "Q.py"
assert Path(teaql.__file__).resolve() == runtime / "src/teaql/__init__.py"
print(Q.__file__)
print(teaql.__file__)
PY
for round in 1 2; do
  "$python" -m app.main "$evidence/orders.sqlite" "$evidence/receipt-$round.txt" "$round" |
    tee "$evidence/run-$round.log"
done
fingerprint > "$evidence/source-after.sha256"
cmp "$evidence/source-before.sha256" "$evidence/source-after.sha256"
printf 'Order attachment evidence retained at %s\n' "$evidence"
