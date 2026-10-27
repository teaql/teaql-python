"""Current-authorized Blob URL projection backed by the optional SQLite catalog."""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Protocol

from teaql.core.object_storage import ObjectKey, ReadUrlOptions
from teaql.runtime.view_preparation import (
    AuthorizedBlobSlot, AuthorizedResponseGraph, ProjectedBlobURL, ViewPreparationError,
)

from .sqlite_catalog import SqliteBlobCatalog


class BlobReadAuthorization(Protocol):
    async def authorize(self, context, slot: AuthorizedBlobSlot) -> bool: ...


class SqliteBlobResponseContributor:
    """Reauthorizes and rereads before requesting complete temporary storage URLs."""

    def __init__(self, catalog: SqliteBlobCatalog,
                 authorization: BlobReadAuthorization, maximum_url_seconds: int = 600):
        if catalog is None or authorization is None or type(maximum_url_seconds) is not int \
                or not 1 <= maximum_url_seconds <= 3600:
            raise RuntimeError("BLOB_POLICY_INVALID")
        self.catalog = catalog
        self.authorization = authorization
        self.maximum_url_seconds = maximum_url_seconds

    async def project_batch(self, context, graph: AuthorizedResponseGraph,
                            expires_at: datetime | None) -> tuple[ProjectedBlobURL, ...]:
        results = []
        for slot in graph.blob_slots:
            try:
                allowed = await self.authorization.authorize(context, slot)
            except Exception:
                raise ViewPreparationError("BLOB_READ_DENIED") from None
            if not allowed:
                raise ViewPreparationError("BLOB_READ_DENIED")
            try:
                record = await self.catalog.current_read(slot)
            except RuntimeError as error:
                code = str(error) if str(error) in ("BLOB_READ_DENIED", "BLOB_CATALOG_FAILED") \
                    else "BLOB_CATALOG_FAILED"
                raise ViewPreparationError(code) from None
            seconds = self.maximum_url_seconds
            if expires_at is not None:
                seconds = min(seconds, int((expires_at - datetime.now(timezone.utc)).total_seconds()) - 1)
            if seconds < 1:
                raise ViewPreparationError("BLOB_REFERENCE_EXPIRED")
            disposition = "inline" if record.content_type.startswith(("image/", "audio/", "video/")) \
                or record.content_type == "application/pdf" else "attachment"
            try:
                signed = await asyncio.to_thread(
                    context.object_storage("prepare authorized Blob view").get_read_url,
                    ObjectKey(record.object_key),
                    ReadUrlOptions(timedelta(seconds=seconds), disposition, record.file_name))
            except Exception:
                raise ViewPreparationError("BLOB_SIGN_FAILED") from None
            results.append(ProjectedBlobURL(signed.url, signed.expires_at))
        return tuple(results)
