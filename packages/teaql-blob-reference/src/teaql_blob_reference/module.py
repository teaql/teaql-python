"""Passive assembly of the optional SQLite Blob reference services."""

from teaql.runtime.capability import install_runtime_capability
from teaql.sql.executor import SqlDataServiceExecutor
from teaql.sql.types import DatabaseKind

from .read_service import SqliteBlobResponseContributor
from .mutation_participant import SqliteBlobMutationParticipant
from .sqlite_catalog import SqliteBlobCatalog
from .upload_service import SqliteBlobUploadService
from .maintenance_service import SqliteBlobMaintenanceService


class _BlobCapability:
    capability = "blob.v1"

    def __init__(self, module: "BlobReferenceModule") -> None:
        self.module = module

    async def validate_ready(self, context) -> None:
        if not isinstance(self.module.upload, SqliteBlobUploadService) or \
                self.module.upload.catalog is not self.module.catalog or \
                self.module.read.catalog is not self.module.catalog or \
                self.module.mutation.catalog is not self.module.catalog or \
                context.get_resource("blob_response_contributor") is not self.module.read or \
                context.get_resource("blob_mutation_participant") is not self.module.mutation or \
                context.get_resource("object_storage_provider") is None:
            raise RuntimeError("BLOB_CAPABILITY_MISSING")
        if self.module.maintenance is not None and \
                (self.module.maintenance.catalog is not self.module.catalog or \
                 context.get_resource("blob_maintenance_service") is not self.module.maintenance):
            raise RuntimeError("BLOB_CAPABILITY_MISSING")
        owner = context.get_resource("dataService")
        try:
            compatible = (isinstance(owner, SqlDataServiceExecutor) and
                          owner.dialect.kind() == DatabaseKind.Sqlite and
                          await owner.uses_sql_database(self.module.catalog.transport))
        except Exception:
            compatible = False
        if not compatible:
            raise RuntimeError("BLOB_CAPABILITY_MISSING")
        await self.module.catalog.validate_schema()
        verifier_ready = getattr(self.module.upload.verifier, "validate_ready", None)
        if callable(verifier_ready):
            verifier_ready()


class BlobReferenceModule:
    """Host installs this module, then separately migrates and checks its catalog."""

    def __init__(self, catalog: SqliteBlobCatalog, upload: SqliteBlobUploadService,
                 read_authorization, binding_authorization, maximum_url_seconds: int = 600,
                 maintenance: SqliteBlobMaintenanceService | None = None):
        if not isinstance(catalog, SqliteBlobCatalog) or \
                not isinstance(upload, SqliteBlobUploadService) or upload.catalog is not catalog or \
                maintenance is not None and (not isinstance(maintenance, SqliteBlobMaintenanceService)
                                            or maintenance.catalog is not catalog):
            raise RuntimeError("BLOB_CAPABILITY_MISSING")
        self.catalog = catalog
        self.upload = upload
        self.mutation = SqliteBlobMutationParticipant(catalog, binding_authorization)
        self.read = SqliteBlobResponseContributor(catalog, read_authorization,
                                                   maximum_url_seconds)
        self.maintenance = maintenance

    def install(self, context) -> None:
        if context is None or context.get_resource("blob_response_contributor") is not None or \
                context.get_resource("blob_mutation_participant") is not None or \
                (self.maintenance is not None and context.get_resource("blob_maintenance_service") is not None) or \
                context.get_resource("teaql.runtime.capability:blob.v1") is not None:
            raise RuntimeError("BLOB_CAPABILITY_MISSING")
        install_runtime_capability(context, _BlobCapability(self))
        context.insert_resource("blob_response_contributor", self.read)
        context.insert_resource("blob_mutation_participant", self.mutation)
        if self.maintenance is not None:
            context.insert_resource("blob_maintenance_service", self.maintenance)

    async def ready(self, context) -> None:
        capability = context.get_resource("teaql.runtime.capability:blob.v1")
        if not isinstance(capability, _BlobCapability) or capability.module is not self:
            raise RuntimeError("BLOB_CAPABILITY_MISSING")
        await capability.validate_ready(context)
