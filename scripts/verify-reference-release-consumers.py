#!/usr/bin/env python3
"""Import exact release wheels in four isolated TeaQL package installations."""

from pathlib import Path
import json
import subprocess
import sys
import tempfile


if len(sys.argv) != 2 or not Path(sys.argv[1]).is_dir():
    raise SystemExit("Usage: verify-reference-release-consumers.py <distribution-directory>")
dist = Path(sys.argv[1]).resolve()
wheels = {
    "base": list(dist.glob("teaql-*-py3-none-any.whl")),
    "blob": list(dist.glob("teaql_blob_reference-*-py3-none-any.whl")),
    "secure": list(dist.glob("teaql_secure_document_reference-*-py3-none-any.whl")),
}
if any(len(files) != 1 for files in wheels.values()):
    raise SystemExit("Expected exactly one wheel per reference package")
variants = {
    "base": ("base",),
    "secure-only": ("base", "secure"),
    "blob-only": ("base", "blob"),
    "combined": ("base", "blob", "secure"),
}
third_party = [path for path in sys.path
               if "site-packages" in path and Path(path).is_dir()]

consumer = r'''
import importlib.util
import json
from pathlib import Path
import sys

target = Path(sys.argv[1]).resolve()
third_party = json.loads(sys.argv[2])
expected_blob = sys.argv[3] == "1"
expected_secure = sys.argv[4] == "1"
sys.path = [str(target)] + [path for path in sys.path if "site-packages" not in path] + third_party

from teaql.runtime import RuntimeModule
assert RuntimeModule.__name__ == "RuntimeModule"
assert Path(importlib.util.find_spec("teaql").origin).resolve().is_relative_to(target)
for module, expected, symbol in (
    ("teaql_blob_reference", expected_blob, "BlobReferenceModule"),
    ("teaql_secure_document_reference", expected_secure, "SecureDocumentReferenceModule"),
):
    spec = importlib.util.find_spec(module)
    assert (spec is not None) == expected, (module, expected)
    if expected:
        package = __import__(module)
        assert getattr(package, symbol).__name__ == symbol
        assert Path(spec.origin).resolve().is_relative_to(target)
print("PASS isolated wheel consumer")
'''

with tempfile.TemporaryDirectory(prefix="teaql-python-release-consumers-") as scratch:
    for variant, packages in variants.items():
        target = Path(scratch) / variant
        target.mkdir()
        command = [sys.executable, "-m", "pip", "install", "--no-index", "--no-deps",
                   "--disable-pip-version-check", "--target", str(target)]
        command.extend(str(wheels[package][0]) for package in packages)
        installed = subprocess.run(command, capture_output=True, text=True)
        if installed.returncode:
            raise SystemExit(f"{variant}: exact wheel install failed: "
                             + (installed.stdout + installed.stderr)[-900:])
        checked = subprocess.run(
            [sys.executable, "-S", "-c", consumer, str(target), json.dumps(third_party),
             "1" if "blob" in packages else "0", "1" if "secure" in packages else "0"],
            cwd=scratch, capture_output=True, text=True,
        )
        if checked.returncode or "PASS isolated wheel consumer" not in checked.stdout:
            raise SystemExit(f"{variant}: isolated wheel import failed: "
                             + (checked.stdout + checked.stderr)[-900:])
        print(f"PASS {variant} exact-wheel consumer")
