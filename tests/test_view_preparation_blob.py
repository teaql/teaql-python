from datetime import datetime, timedelta, timezone

import pytest

from teaql.core.blob_ref import BlobRef
from teaql.runtime.context import UserContext
from teaql.runtime.view_preparation import (
    AuthorizedBlobSlot, AuthorizedResponseGraph, PreparedSecureDocument,
    ProjectedBlobURL, ViewOptions, ViewPreparationError, ViewPreparationService,
)


@pytest.mark.asyncio
async def test_authorized_view_is_detached_and_governed_document_precedes_blob_url():
    reference = BlobRef("blob_asset_1")
    source = {"document": reference, "nested": [{"title": "untouched"}]}
    stages = []
    ceiling = datetime.now(timezone.utc) + timedelta(minutes=5)

    class Authorizer:
        async def authorize(self, _context, _result, _options):
            stages.append("authorize")
            return AuthorizedResponseGraph(source, (AuthorizedBlobSlot(
                path=("document",), entity="Asset", entity_id="1", field="document",
                scope="tenant-a", binding_version=4, reference=reference),))

    class Secure:
        async def prepare(self, _context, graph, _options):
            stages.append("secure")
            graph.presentation["governed"] = True
            return PreparedSecureDocument(graph, "sealed-document", ceiling)

    class Blob:
        async def project_batch(self, _context, graph, expiry):
            stages.append("blob")
            assert expiry == ceiling
            assert graph.blob_slots[0].reference == reference
            return (ProjectedBlobURL("https://files.example.invalid/read/asset",
                                     ceiling - timedelta(minutes=1)),)

    context = UserContext()
    context.insert_resource("response_graph_authorizer", Authorizer())
    context.insert_resource("secure_document_contributor", Secure())
    context.insert_resource("blob_response_contributor", Blob())
    view = await ViewPreparationService().prepare(context, source,
        ViewOptions(mode="governed", business_outcome="committed"))
    assert stages == ["authorize", "secure", "blob"]
    assert source == {"document": reference, "nested": [{"title": "untouched"}]}
    assert view.presentation == {
        "document": "https://files.example.invalid/read/asset",
        "nested": [{"title": "untouched"}], "governed": True,
    }
    assert view.document == "sealed-document"
    assert view.expires_at == ceiling - timedelta(minutes=1)
    assert view.cache_control == "private, no-store"


@pytest.mark.asyncio
async def test_independent_url_lifetimes_use_original_ceiling_and_minimum():
    first = BlobRef("blob_asset_1")
    second = BlobRef("blob_asset_2")
    ceiling = datetime.now(timezone.utc) + timedelta(seconds=90)
    first_expiry = datetime.now(timezone.utc) + timedelta(seconds=20)
    second_expiry = datetime.now(timezone.utc) + timedelta(seconds=40)

    class Authorizer:
        async def authorize(self, _context, _result, _options):
            return AuthorizedResponseGraph({"first": first, "second": second}, (
                AuthorizedBlobSlot(("first",), "Asset", "1", "first", "tenant-a", 4, first),
                AuthorizedBlobSlot(("second",), "Asset", "1", "second", "tenant-a", 5, second),
            ))

    class Blob:
        async def project_batch(self, _context, _graph, expiry):
            assert expiry == ceiling
            return (ProjectedBlobURL("https://files.example.invalid/first", first_expiry),
                    ProjectedBlobURL("https://files.example.invalid/second", second_expiry))

    context = UserContext()
    context.insert_resource("response_graph_authorizer", Authorizer())
    context.insert_resource("blob_response_contributor", Blob())
    view = await ViewPreparationService().prepare(context, None,
        ViewOptions(mode="ordinary", business_outcome="read_only", expires_at=ceiling))
    assert view.expires_at == first_expiry
    assert view.presentation == {
        "first": "https://files.example.invalid/first",
        "second": "https://files.example.invalid/second",
    }


@pytest.mark.asyncio
async def test_unlisted_key_and_provider_failure_fail_closed_after_commit():
    reference = BlobRef("blob_private_canary")

    class Authorizer:
        def __init__(self):
            self.listed = False

        async def authorize(self, _context, _result, _options):
            slots = (AuthorizedBlobSlot(("document",), "Asset", "1", "document",
                                        "tenant-a", 4, reference),) if self.listed else ()
            return AuthorizedResponseGraph({"document": reference}, slots)

    class FailingBlob:
        async def project_batch(self, _context, _graph, _expiry):
            raise RuntimeError("private URL https://secret.invalid/read?sig=canary")

    authorizer = Authorizer()
    context = UserContext().insert_resource("response_graph_authorizer", authorizer)
    service = ViewPreparationService()
    options = ViewOptions(mode="ordinary", business_outcome="committed")
    with pytest.raises(ViewPreparationError) as first:
        await service.prepare(context, None, options)
    assert first.value.code == "BLOB_CAPABILITY_MISSING"
    assert first.value.business_state == "committed"
    assert first.value.retry == "read"
    assert reference.key not in str(first.value)

    authorizer.listed = True
    context.insert_resource("blob_response_contributor", FailingBlob())
    with pytest.raises(ViewPreparationError) as second:
        await service.prepare(context, None, options)
    assert second.value.code == "VIEW_PREPARATION_FAILED"
    assert "secret.invalid" not in str(second.value)


@pytest.mark.asyncio
async def test_invalid_or_expired_view_options_are_rejected_before_authorization():
    context = UserContext()
    service = ViewPreparationService()
    for options in (
        None,
        ViewOptions(mode="downgrade", business_outcome="read_only"),
        ViewOptions(mode="ordinary", business_outcome="committed",
                    expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)),
    ):
        with pytest.raises(ViewPreparationError) as failure:
            await service.prepare(context, {}, options)
        assert failure.value.code == "VIEW_OPTIONS_INVALID"
