"""Passive assembly of the optional SQLite Blob reference services."""

from teaql.runtime.capability import install_runtime_capability

from .read_service import SqliteBlobResponseContributor
from .mutation_participant import SqliteBlobMutationParticipant
from .sqlite_catalog import SqliteBlobCatalog
from .upload_service import SqliteBlobUploadService


class _BlobCapability:
    capability = "blob.v1"

    def __init__(self, module: "BlobReferenceModule") -> None:
        self.module = module

    async def validate_ready(self, context) -> None:
        if context.get_resource("blob_response_contributor") is not self.module.read or \
                context.get_resource("blob_mutation_participant") is not self.module.mutation or \
                context.get_resource("object_storage_provider") is None:
            raise RuntimeError("BLOB_CAPABILITY_MISSING")
        owner = context.get_resource("dataService")
        if owner is None or not callable(getattr(owner, "begin", None)):
            raise RuntimeError("BLOB_CAPABILITY_MISSING")
        await self.module.catalog.validate_schema()
        verifier_ready = getattr(self.module.upload.verifier, "validate_ready", None)
        if callable(verifier_ready):
            verifier_ready()


class BlobReferenceModule:
    """Host installs this module, then separately migrates and checks its catalog."""

    def __init__(self, catalog: SqliteBlobCatalog, upload: SqliteBlobUploadService,
                 read_authorization, binding_authorization, maximum_url_seconds: int = 600):
        if not isinstance(catalog, SqliteBlobCatalog) or \
                not isinstance(upload, SqliteBlobUploadService) or upload.catalog is not catalog:
            raise RuntimeError("BLOB_CAPABILITY_MISSING")
        self.catalog = catalog
        self.upload = upload
        self.mutation = SqliteBlobMutationParticipant(catalog, binding_authorization)
        self.read = SqliteBlobResponseContributor(catalog, read_authorization,
                                                   maximum_url_seconds)

    def install(self, context) -> None:
        if context is None or context.get_resource("blob_response_contributor") is not None or \
                context.get_resource("blob_mutation_participant") is not None or \
                context.get_resource("teaql.runtime.capability:blob.v1") is not None:
            raise RuntimeError("BLOB_CAPABILITY_MISSING")
        install_runtime_capability(context, _BlobCapability(self))
        context.insert_resource("blob_response_contributor", self.read)
        context.insert_resource("blob_mutation_participant", self.mutation)

    async def ready(self, context) -> None:
        capability = context.get_resource("teaql.runtime.capability:blob.v1")
        if not isinstance(capability, _BlobCapability) or capability.module is not self:
            raise RuntimeError("BLOB_CAPABILITY_MISSING")
        await capability.validate_ready(context)
