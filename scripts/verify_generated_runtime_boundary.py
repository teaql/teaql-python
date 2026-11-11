"""Reject embedded runtimes; allow only hashed generator provenance metadata."""
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
        if len(children) != 1 or children[0] != metadata or metadata.is_symlink() or not metadata.is_file():
            raise ValueError(f"embedded teaql runtime snapshot: {package}")
        if manifest.is_symlink() or not manifest.is_file():
            raise ValueError(f"unowned generator provenance: {package}")
        expected = json.loads(manifest.read_text()).get("teaql/model-provenance.json")
        if expected != hashlib.sha256(metadata.read_bytes()).hexdigest():
            raise ValueError(f"generator provenance hash mismatch: {metadata}")
        if json.loads(metadata.read_text()).get("schemaVersion") != 1:
            raise ValueError(f"unknown generator provenance schema: {metadata}")
    for module in Path(examples).rglob("teaql.py"):
        raise ValueError(f"embedded teaql runtime module: {module}")


if __name__ == "__main__":
    verify(Path(sys.argv[1]))
    print("PASS generated runtime boundary: packaged runtime only; hashed metadata is not executable source")
