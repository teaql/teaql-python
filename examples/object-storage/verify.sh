#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
: "${TEAQL_S3_ENDPOINT:?dedicated local test endpoint required}"
: "${TEAQL_S3_BUCKET:?dedicated test bucket required}"
: "${TEAQL_S3_ACCESS_KEY:?test access key required}"
: "${TEAQL_S3_SECRET_KEY:?test secret key required}"
cd "$repo"
export PYTHONPATH="$repo/src"
export PYTHONDONTWRITEBYTECODE=1
"${PYTHON:-python3}" -m pytest tests/runtime/test_object_storage.py -q
"${PYTHON:-python3}" examples/object-storage/main.py
