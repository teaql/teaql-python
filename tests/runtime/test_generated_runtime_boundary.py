import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("runtime_boundary", Path(__file__).resolve().parents[2] / "scripts/verify_generated_runtime_boundary.py")
boundary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(boundary)


def metadata(root):
    package = root / "fixture/teaql"
    package.mkdir(parents=True)
    file = package / "model-provenance.json"
    file.write_text(json.dumps({"schemaVersion": 1, "generatorVersion": "fixture"}))
    (package.parent / "generated-files.json").write_text(json.dumps({"teaql/model-provenance.json": hashlib.sha256(file.read_bytes()).hexdigest()}))
    return package


def test_only_owned_hashed_nonexecutable_metadata_is_allowed(tmp_path):
    metadata(tmp_path)
    boundary.verify(tmp_path)


@pytest.mark.parametrize("name", ("__init__.py", "runtime.py", "runtime.pyc"))
def test_metadata_cannot_hide_embedded_runtime_sources_or_bytecode(tmp_path, name):
    package = metadata(tmp_path)
    (package / name).write_text("forbidden")
    with pytest.raises(ValueError, match="embedded teaql runtime"):
        boundary.verify(tmp_path)


def test_changed_or_unowned_metadata_does_not_bypass_the_guard(tmp_path):
    package = metadata(tmp_path)
    (package / "model-provenance.json").write_text('{"schemaVersion":1}')
    with pytest.raises(ValueError, match="hash mismatch"):
        boundary.verify(tmp_path)


def test_provenance_symlink_is_rejected(tmp_path):
    package = metadata(tmp_path)
    actual = tmp_path / "external.json"
    (package / "model-provenance.json").rename(actual)
    (package / "model-provenance.json").symlink_to(actual)
    with pytest.raises(ValueError):
        boundary.verify(tmp_path)
