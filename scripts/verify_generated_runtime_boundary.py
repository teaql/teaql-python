"""Reject embedded runtimes; allow only enumerated, hashed passive metadata."""
import hashlib
import json
from pathlib import Path
import sys


def verify(examples):
    for package in Path(examples).rglob("teaql"):
        if package.is_symlink() or not package.is_dir():
            raise ValueError(f"unexpected generated teaql namespace: {package}")
        children = list(package.iterdir())
        metadata = package / "model-provenance.json"
        manifest = package.parent / "generated-files.json"
        allowed = {"model-provenance.json", "checker-model.json"}
        if (not children or {file.name for file in children} - allowed
                or metadata not in children or any(file.is_symlink() or not file.is_file() for file in children)):
            raise ValueError(f"embedded teaql runtime snapshot: {package}")
        if manifest.is_symlink() or not manifest.is_file():
            raise ValueError(f"unowned generator provenance: {package}")
        hashes = json.loads(manifest.read_text())
        for file in children:
            if hashes.get("teaql/" + file.name) != hashlib.sha256(file.read_bytes()).hexdigest():
                raise ValueError(f"generator metadata hash mismatch: {file}")
        if json.loads(metadata.read_text()).get("schemaVersion") != 1:
            raise ValueError(f"unknown generator provenance schema: {metadata}")
        checker = package / "checker-model.json"
        if checker in children and json.loads(checker.read_text()).get("schema") != "teaql.checker-model/v1":
            raise ValueError(f"unknown checker presentation schema: {checker}")
    for module in Path(examples).rglob("teaql.py"):
        raise ValueError(f"embedded teaql runtime module: {module}")


if __name__ == "__main__":
    verify(Path(sys.argv[1]))
    print("PASS generated runtime boundary: packaged runtime only; hashed metadata is not executable source")
