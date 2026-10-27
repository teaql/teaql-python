"""The optional Blob assembly fails closed until the owner and catalog are ready."""

import os

import pytest

from teaql.provider.sqlite import SimpleSchemaProvider
from teaql.provider.sqlite.dialect import SqliteDialect
from teaql.provider.sqlite.transport import SqliteTransport
from teaql.runtime import RuntimeModule, validate_capabilities
from teaql.sql.executor import SqlDataServiceExecutor
from teaql_blob_reference import (
    BlobReferenceModule, FileObjectStorage, SqliteBlobCatalog, SqliteBlobUploadService,
)


class _ReadAuthority:
    async def authorize(self, context, slot):
        return True


class _UploadAuthority:
    def scope(self, context):
        return "tenant-a"

    def field(self, context, target):
        raise AssertionError("readiness must not begin an upload")

    async def authorize(self, context, target, action, input):
        return True


class _Verifier:
    def verify(self, stream, extension, maximum_bytes):
        raise AssertionError("readiness must not parse content")


@pytest.mark.asyncio
async def test_blob_module_requires_provider_owner_and_catalog(tmp_path):
    path = str(tmp_path / "module.db")
    transport = SqliteTransport(path)
    catalog = SqliteBlobCatalog(transport)
    upload = SqliteBlobUploadService(catalog, _UploadAuthority(), _Verifier(), 10_000)
    module = BlobReferenceModule(catalog, upload, _ReadAuthority())
    context = RuntimeModule.new().require_capability("blob.v1").into_context()
    with pytest.raises(RuntimeError, match="BLOB_CAPABILITY_MISSING"):
        await validate_capabilities(context)
    module.install(context)
    assert context.get_resource("blob_response_contributor") is module.read
    with pytest.raises(RuntimeError, match="BLOB_CAPABILITY_MISSING"):
        await module.ready(context)
    with pytest.raises(RuntimeError, match="BLOB_CAPABILITY_MISSING"):
        module.install(context)

    context.insert_resource("dataService", SqlDataServiceExecutor(
        SqliteDialect(), SqliteTransport(path), SimpleSchemaProvider()))
    provider = FileObjectStorage(tmp_path / "private", os.urandom(32))
    context.with_object_storage(provider)
    with pytest.raises(RuntimeError, match="BLOB_SCHEMA_MISSING"):
        await module.ready(context)
    await catalog.ensure_schema()
    await module.ready(context)
    await validate_capabilities(context)
    provider.close()


def test_blob_module_rejects_an_upload_from_another_catalog(tmp_path):
    first = SqliteBlobCatalog(SqliteTransport(str(tmp_path / "first.db")))
    second = SqliteBlobCatalog(SqliteTransport(str(tmp_path / "second.db")))
    upload = SqliteBlobUploadService(second, _UploadAuthority(), _Verifier(), 10_000)
    with pytest.raises(RuntimeError, match="BLOB_CAPABILITY_MISSING"):
        BlobReferenceModule(first, upload, _ReadAuthority())
