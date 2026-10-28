#!/usr/bin/env python3
"""Install the exact reference release wheels and declared extras in clean venvs."""

from pathlib import Path
import hashlib
import os
import subprocess
import sys
import tempfile


if len(sys.argv) != 2 or not Path(sys.argv[1]).is_dir():
    raise SystemExit("Usage: verify-reference-release-dependencies.py <distribution-directory>")
DIST = Path(sys.argv[1]).resolve()


def run(args, *, cwd, env, timeout=900):
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True,
                            timeout=timeout)
    if result.returncode:
        raise RuntimeError(" ".join(map(str, args)) + " failed:\n"
                           + (result.stdout + result.stderr)[-5000:])
    return result.stdout + result.stderr


def exact_wheels():
    names = {
        "base": "teaql-",
        "blob": "teaql_blob_reference-",
        "secure": "teaql_secure_document_reference-",
    }
    result = {}
    for name, prefix in names.items():
        found = [path for path in DIST.glob("*.whl")
                 if path.name.startswith(prefix) and path.name.endswith("-py3-none-any.whl")]
        if len(found) != 1:
            raise RuntimeError("expected exactly one " + name + " release wheel")
        result[name] = found[0]
    return result


CHECK = r'''
from importlib import metadata, util
from pathlib import Path
import sys

root = Path(sys.prefix).resolve()
variant = sys.argv[1]
blob = variant in ("blob-only", "combined")
secure = variant in ("secure-only", "combined")
for distribution, expected in (
    ("teaql", True),
    ("teaql-blob-reference", blob),
    ("teaql-secure-document-reference", secure),
):
    try:
        installed = metadata.distribution(distribution)
    except metadata.PackageNotFoundError:
        installed = None
    assert (installed is not None) == expected, (variant, distribution)
    if installed is not None:
        assert Path(installed.locate_file("")).resolve().is_relative_to(root), distribution
from teaql.runtime import RuntimeModule
assert RuntimeModule.__name__ == "RuntimeModule"
assert (util.find_spec("teaql_blob_reference") is not None) == blob
assert (util.find_spec("teaql_secure_document_reference") is not None) == secure
if blob:
    from teaql_blob_reference import BlobReferenceModule
    from teaql_blob_reference.content_pillow import PillowBlobContentVerifier
    from teaql_blob_reference.content_pypdf import PypdfBlobContentVerifier
    from teaql_blob_reference.content_office import OfficeBlobContentVerifier
    from teaql.provider.s3 import S3ObjectStorage
    import boto3
    assert BlobReferenceModule.__name__ == "BlobReferenceModule"
    assert S3ObjectStorage.__name__ == "S3ObjectStorage"
    assert boto3.__version__
    PillowBlobContentVerifier().validate_ready()
    PypdfBlobContentVerifier().validate_ready()
    OfficeBlobContentVerifier().validate_ready()
else:
    assert util.find_spec("boto3") is None
    assert util.find_spec("PIL") is None
if secure:
    from teaql_secure_document_reference import SecureDocumentReferenceModule
    assert SecureDocumentReferenceModule.__name__ == "SecureDocumentReferenceModule"
if variant == "combined":
    from teaql.runtime.opentelemetry import OpenTelemetryRuntimeTelemetry
    import opentelemetry.sdk
    assert OpenTelemetryRuntimeTelemetry.__name__ == "OpenTelemetryRuntimeTelemetry"
print("PASS isolated dependency consumer " + variant)
'''


def main():
    wheels = exact_wheels()
    with tempfile.TemporaryDirectory(prefix="teaql-python-release-dependencies-") as temporary:
        work = Path(temporary)
        wheelhouse = work / "wheelhouse"
        wheelhouse.mkdir()
        environment = dict(os.environ, PIP_CACHE_DIR=str(work / "pip-cache"),
                           PIP_DISABLE_PIP_VERSION_CHECK="1", PIP_NO_INPUT="1",
                           PIP_PROGRESS_BAR="off", PYTHONNOUSERSITE="1")
        environment.pop("PYTHONPATH", None)
        inputs = [
            str(wheels["base"]) + "[object-storage-s3,telemetry]",
            str(wheels["blob"]) + "[image,pdf,office]",
            str(wheels["secure"]),
        ]
        run([sys.executable, "-m", "pip", "download", "--only-binary=:all:",
             "--dest", str(wheelhouse), *inputs], cwd=work, env=environment)
        for name, candidate in wheels.items():
            copy = wheelhouse / candidate.name
            if not copy.is_file() or copy.read_bytes() != candidate.read_bytes():
                raise RuntimeError(name + " candidate wheel not retained exactly")
            print("PASS exact " + name + " wheel_sha256="
                  + hashlib.sha256(candidate.read_bytes()).hexdigest(), flush=True)
        resolved = sorted(wheelhouse.glob("*.whl"))
        manifest = "\n".join(
            path.name + " " + hashlib.sha256(path.read_bytes()).hexdigest()
            for path in resolved
        ).encode()
        print("PASS resolved wheelhouse count=" + str(len(resolved))
              + " manifest_sha256=" + hashlib.sha256(manifest).hexdigest(), flush=True)
        cases = {
            "base": (str(wheels["base"]),),
            "secure-only": (str(wheels["base"]), str(wheels["secure"])),
            "blob-only": (str(wheels["base"]) + "[object-storage-s3]",
                          str(wheels["blob"]) + "[image,pdf,office]"),
            "combined": (str(wheels["base"]) + "[object-storage-s3,telemetry]",
                         str(wheels["blob"]) + "[image,pdf,office]", str(wheels["secure"])),
        }
        for name, packages in cases.items():
            venv = work / name
            run([sys.executable, "-m", "venv", str(venv)], cwd=work, env=environment)
            python = venv / "bin/python"
            run([str(python), "-I", "-m", "pip", "install", "--no-index",
                 "--find-links", str(wheelhouse), "--only-binary=:all:",
                 "--no-cache-dir", *packages], cwd=work, env=environment)
            run([str(python), "-I", "-m", "pip", "check"], cwd=work, env=environment)
            output = run([str(python), "-I", "-c", CHECK, name],
                         cwd=work, env=environment)
            if "PASS isolated dependency consumer " + name not in output:
                raise RuntimeError(name + " application did not run")
            print("PASS isolated dependency consumer " + name, flush=True)
    print("PASS exact Python release-wheel dependency closure 4/4", flush=True)


if __name__ == "__main__":
    main()
