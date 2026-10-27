import json
from pathlib import Path

import pytest

from teaql.core import BlobFieldSpec, BlobRef
from teaql.runtime import RuntimeModule, UserContext, install_runtime_capability, validate_capabilities


VECTORS = json.loads((Path(__file__).resolve().parents[2] / "test-vectors" /
                      "blob-value-cases.json").read_text())


def test_shared_blob_ref_and_format_vectors():
    for key in VECTORS["valid"]:
        reference = BlobRef.from_json(key)
        assert reference == BlobRef.from_sql(key)
        assert reference.to_sql() == key
        assert repr(reference) == "BlobRef[masked]"
        with pytest.raises(TypeError):
            json.dumps(reference)
        with pytest.raises(AttributeError):
            reference._key = "blob_other"
    for value in [*VECTORS["invalid"], *VECTORS["invalidJson"]]:
        with pytest.raises(ValueError, match="BLOB_REFERENCE_INVALID"):
            BlobRef.from_json(value)

    spec = BlobFieldSpec("Asset", "document", list(reversed(VECTORS["formats"])),
                         False, "default")
    assert spec.allowed_extensions == tuple(sorted(VECTORS["formats"]))
    assert spec.allowed_content_types == tuple(sorted(set(VECTORS["formats"].values())))
    with pytest.raises(ValueError, match="BLOB_FORMAT_NOT_ALLOWED"):
        BlobFieldSpec("Asset", "document", ["application.docx"], False, "default")


class ReadyResource:
    def __init__(self, capability: str, failure: bool = False):
        self.capability = capability
        self.failure = failure

    async def validate_ready(self, context):
        if self.failure:
            raise RuntimeError("private provider diagnostic")


@pytest.mark.asyncio
async def test_module_capabilities_fail_before_graph_transaction_and_schema():
    blob = RuntimeModule.new().require_capability("blob.v1")
    secure = RuntimeModule.new().require_capability("secure_document.v1").require_capability("blob.v1")
    both = blob.and_module(secure)
    assert both.required_capabilities == ("blob.v1", "secure_document.v1")
    assert blob.required_capabilities == ("blob.v1",)
    context = both.into_context()
    entered = False

    async def work(_session):
        nonlocal entered
        entered = True

    with pytest.raises(RuntimeError, match="BLOB_CAPABILITY_MISSING"):
        await context.execute_graph_save(work, comment="save document")
    assert not entered
    with pytest.raises(RuntimeError, match="BLOB_CAPABILITY_MISSING"):
        await context.ensure_schema()

    install_runtime_capability(context, ReadyResource("blob.v1"))
    with pytest.raises(RuntimeError, match="DOCUMENT_CONFIGURATION"):
        await validate_capabilities(context)
    install_runtime_capability(context, ReadyResource("secure_document.v1"))
    await validate_capabilities(context)
    with pytest.raises(ValueError, match="RUNTIME_CAPABILITY_DUPLICATE"):
        install_runtime_capability(context, ReadyResource("blob.v1"))

    failing = RuntimeModule.new().require_capability("blob.v1").into_context()
    install_runtime_capability(failing, ReadyResource("blob.v1", failure=True))
    with pytest.raises(RuntimeError, match="BLOB_CAPABILITY_MISSING") as error:
        await validate_capabilities(failing)
    assert "private provider diagnostic" not in str(error.value)
