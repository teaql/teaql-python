from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
from datetime import timedelta

import pytest

from teaql_secure_document_reference import (
    BlobSelectionClaim, BlobSelectionTarget, BoundDocumentSnapshot,
    DocumentBlobBindingSnapshot, DocumentEntitySnapshot, DocumentRelationSnapshot,
    DocumentSnapshot, ReferenceDocumentScope, ReferenceIdentity, ReferenceKey,
    RoundTripReferenceError, SecureDocumentReferenceModule, StaticReferenceKeyProvider,
    TrustedReferencePrincipal, PreparedBoundDocument,
)
from teaql.core.blob_ref import BlobRef
from teaql.runtime.context import UserContext
from teaql.runtime.capability import validate_capabilities
from teaql.runtime.view_preparation import (
    AuthorizedBlobSlot, AuthorizedResponseGraph, ProjectedBlobURL,
    ViewOptions, ViewPreparationError, ViewPreparationService,
)


NOW = datetime.fromtimestamp(1800000000, timezone.utc)
ALICE = TrustedReferencePrincipal("oidc", "alice", "Merchant", 7)
SCOPE = ReferenceDocumentScope("doc-1", "edit-order", "Order", 10, 4)
SNAPSHOT = DocumentSnapshot("model-v1", "ORD-X1", SCOPE,
                            ReferenceIdentity("Order", 10, 4),
                            (DocumentEntitySnapshot("item:0", ReferenceIdentity("OrderItem", 20, 2),
                                                    frozenset(("attachment", "product_code", "quantity")),
                                                    frozenset(("attachment", "quantity")),
                                                    frozenset(("UPDATE",))),),
                            (DocumentRelationSnapshot("items", ("item:0",), "COMPLETE", True,
                                                      frozenset(("CREATE_CHILD", "REMOVE_CHILD"))),))
DOCUMENT = BoundDocumentSnapshot(SNAPSHOT,
                                 (DocumentBlobBindingSnapshot("item:0", "attachment", "OrderItem",
                                                              "blob_A", (1 << 64) - 1, True, True),))
TARGET = BlobSelectionTarget(SCOPE, "OrderItem", "attachment", "EXISTING_ROW", "item:0", "command-1")
CLAIM = BlobSelectionClaim(TARGET, "blob_B")
KEYS = StaticReferenceKeyProvider("k1", (ReferenceKey("k1", bytes([0x42]) * 32),))


def runtime(*, now=NOW, allowed=True, environment="test"):
    def authorize(*_args):
        if not allowed:
            raise PermissionError("revoked")
    return SecureDocumentReferenceModule("order-service", environment, KEYS, authorize,
                                         lambda: now, lambda: bytes([0x33]) * 12)


def code(call):
    with pytest.raises(RoundTripReferenceError) as error:
        call()
    return error.value.code


def test_shared_tqd2_tqs1_vectors_and_current_authorization():
    module = runtime()
    token = module.issue_bound_document_snapshot(ALICE, DOCUMENT, 300)
    assert sha256(token.encode()).hexdigest() == \
        "e7c81ca089b0a3e0585faefcc275aeb44b456d666d9a4a17949c92b1891089d7"
    verified = module.consume_bound_document_snapshot(ALICE, token, "Order", "edit-order")
    assert verified.document == DOCUMENT
    selection = module.issue_blob_selection(ALICE, token, CLAIM, 120)
    assert sha256(selection.encode()).hexdigest() == \
        "31303e3e251dd0e8963bf2a4d8897d1eccde63a485aaf287f88f29d40757ba96"
    assert module.consume_blob_selection(ALICE, token, selection, TARGET).document == CLAIM
    assert code(lambda: runtime(allowed=False).consume_bound_document_snapshot(
        ALICE, token, "Order", "edit-order")) == "ROUND_TRIP_REFERENCE_AUTHORIZATION_REQUIRED"


def test_legacy_tqd1_rust_digest_and_v2_separation():
    legacy_entity = replace(SNAPSHOT.entities[0],
                            loaded_fields=frozenset(("product_code", "quantity")),
                            writable_fields=frozenset(("quantity",)))
    legacy = replace(SNAPSHOT, entities=(legacy_entity,))
    token = runtime().issue_document_snapshot(ALICE, legacy, 600)
    assert sha256(token.encode()).hexdigest() == \
        "69fee1ec01cd4a5b69dd3f795aeaffb3a3546e50d48e25cfc9b8f169a527b267"
    assert runtime().consume_document_snapshot(ALICE, token, "Order", "edit-order").document == legacy
    assert code(lambda: runtime().consume_bound_document_snapshot(ALICE, token, "Order", "edit-order")) == \
        "ROUND_TRIP_REFERENCE_INVALID"


def test_tamper_wrong_actor_context_target_and_expiry():
    token = runtime().issue_bound_document_snapshot(ALICE, DOCUMENT, 300)
    selection = runtime().issue_blob_selection(ALICE, token, CLAIM, 120)
    assert code(lambda: runtime().consume_bound_document_snapshot(
        replace(ALICE, subject="bob"), token, "Order", "edit-order")) == \
        "ROUND_TRIP_REFERENCE_SCOPE_MISMATCH"
    assert code(lambda: runtime(environment="other").consume_bound_document_snapshot(
        ALICE, token, "Order", "edit-order")) == "ROUND_TRIP_REFERENCE_INVALID"
    assert code(lambda: runtime().consume_blob_selection(
        ALICE, token, selection, replace(TARGET, command_id="other"))) == \
        "ROUND_TRIP_REFERENCE_SCOPE_MISMATCH"
    assert code(lambda: runtime(now=datetime.fromtimestamp(1800000120, timezone.utc)).consume_blob_selection(
        ALICE, token, selection, TARGET)) == "ROUND_TRIP_REFERENCE_EXPIRED"
    assert code(lambda: runtime().consume_blob_selection(ALICE, token, selection + "A", TARGET)) == \
        "ROUND_TRIP_REFERENCE_INVALID"
    assert code(lambda: runtime().consume_blob_selection(ALICE, token, "blob_B", TARGET)) == \
        "ROUND_TRIP_REFERENCE_INVALID"
    assert code(lambda: runtime().issue_blob_selection(ALICE, token,
                                                       replace(CLAIM, stable_key="https://example.test/file"), 120)) == \
        "ROUND_TRIP_REFERENCE_INVALID"


@pytest.mark.asyncio
async def test_passive_install_prepares_governed_view_and_checks_blob_binding():
    now = datetime.now(timezone.utc)
    module = runtime(now=now)
    bound = replace(DOCUMENT, bindings=(replace(DOCUMENT.bindings[0], binding_version=4),))
    reference = BlobRef("blob_A")
    graph = AuthorizedResponseGraph({"attachment": reference},
                                    (AuthorizedBlobSlot(("attachment",), "OrderItem", "20",
                                                        "attachment", "tenant-a", 4, reference),))

    class Authorizer:
        async def authorize(self, _context, _result, _options):
            return graph

    class Projector:
        async def project_batch(self, _context, _graph, _expiry):
            return (ProjectedBlobURL("https://files.example.invalid/private/asset",
                                     datetime.now(timezone.utc) + timedelta(seconds=30)),)

    class Assembly:
        def __init__(self, document):
            self.document = document

        def principal(self, _context):
            return ALICE

        async def snapshot(self, _context, _graph):
            return PreparedBoundDocument(self.document, 300)

    context = UserContext().insert_resource("response_graph_authorizer", Authorizer())
    context.insert_resource("blob_response_contributor", Projector())
    module.install(context, Assembly(bound))
    context._required_capabilities = frozenset(("secure_document.v1",))
    await validate_capabilities(context)
    with pytest.raises(RuntimeError, match="DOCUMENT_CONFIGURATION"):
        module.install(context, Assembly(bound))
    view = await ViewPreparationService().prepare(
        context, None, ViewOptions("governed", "committed"))
    assert view.presentation == {"attachment": "https://files.example.invalid/private/asset"}
    assert view.document["documentToken"].startswith("tqd2.k1.")
    assert view.expires_at <= datetime.now(timezone.utc) + timedelta(seconds=30)
    context.insert_resource("teaql.runtime.capability:secure_document.v1", None)
    with pytest.raises(ViewPreparationError) as missing:
        await ViewPreparationService().prepare(context, None, ViewOptions("governed", "committed"))
    assert missing.value.code == "DOCUMENT_CONFIGURATION"

    wrong = UserContext().insert_resource("response_graph_authorizer", Authorizer())
    module.install(wrong, Assembly(replace(bound, bindings=(replace(bound.bindings[0],
                                                            stable_key="blob_other"),))))
    with pytest.raises(ViewPreparationError) as error:
        await ViewPreparationService().prepare(wrong, None, ViewOptions("governed", "committed"))
    assert (error.value.code, error.value.business_state, error.value.retry) == \
        ("DOCUMENT_PROJECTION_VIOLATION", "committed", "read")


@pytest.mark.parametrize("scenario", ["writable-unloaded", "duplicate-row", "orphan-relation",
    "duplicate-relation-row", "readonly-relation-mutation", "binding-unloaded",
    "binding-readonly", "binding-foreign-entity", "duplicate-binding"])
def test_rejects_inconsistent_issued_projection(scenario):
    row, relation, binding = SNAPSHOT.entities[0], SNAPSHOT.relations[0], DOCUMENT.bindings[0]
    if scenario == "writable-unloaded": row = replace(row, writable_fields=frozenset({"hidden"}))
    if scenario == "orphan-relation": relation = replace(relation, row_keys=("absent",))
    if scenario == "duplicate-relation-row": relation = replace(relation, row_keys=("item:0", "item:0"))
    if scenario == "readonly-relation-mutation": relation = replace(relation, writable=False)
    if scenario == "binding-unloaded":
        row = replace(row, loaded_fields=frozenset({"quantity"}), writable_fields=frozenset({"quantity"}))
        binding = replace(binding, writable=False)
    if scenario == "binding-readonly": row = replace(row, writable_fields=frozenset({"quantity"}))
    if scenario == "binding-foreign-entity": binding = replace(binding, entity_type="OtherItem")
    snapshot = replace(SNAPSHOT, entities=(row, row) if scenario == "duplicate-row" else (row,),
                       relations=(relation,))
    document = replace(DOCUMENT, snapshot=snapshot,
                       bindings=(binding, binding) if scenario == "duplicate-binding" else (binding,))
    assert code(lambda: runtime().issue_bound_document_snapshot(ALICE, document, 60)) == \
        "DOCUMENT_PROJECTION_VIOLATION"


@pytest.mark.parametrize("scenario", ["readonly-existing", "hidden-existing", "partial-child",
                                      "readonly-child", "no-create-child"])
def test_selection_cannot_expand_the_issued_surface(scenario):
    document, target = DOCUMENT, TARGET
    if scenario == "readonly-existing":
        row = replace(SNAPSHOT.entities[0], writable_fields=frozenset({"quantity"}))
        document = replace(DOCUMENT, snapshot=replace(SNAPSHOT, entities=(row,)),
                           bindings=(replace(DOCUMENT.bindings[0], writable=False),))
    elif scenario == "hidden-existing": target = replace(TARGET, canonical_field="hidden_attachment")
    else:
        target = replace(TARGET, kind="NEW_CLIENT_KEY", target_key="client-hidden")
        relation = SNAPSHOT.relations[0]
        if scenario == "partial-child": relation = replace(relation, completeness="PARTIAL")
        if scenario == "readonly-child": relation = replace(relation, writable=False, allowed_mutations=frozenset())
        if scenario == "no-create-child": relation = replace(relation, allowed_mutations=frozenset({"REMOVE_CHILD"}))
        document = replace(DOCUMENT, snapshot=replace(SNAPSHOT, relations=(relation,)))
    module = runtime()
    token = module.issue_bound_document_snapshot(ALICE, document, 60)
    assert module.consume_bound_document_snapshot(ALICE, token, "Order", "edit-order").document == document
    assert code(lambda: module.issue_blob_selection(ALICE, token, replace(CLAIM, target=target), 30)) == \
        "DOCUMENT_PROJECTION_VIOLATION"


@pytest.mark.asyncio
async def test_governed_view_hides_unlisted_blob_and_bounds_url_by_document_deadline():
    now = datetime.now(timezone.utc).replace(microsecond=0)
    deadline = now + timedelta(seconds=60)
    visible, hidden = BlobRef("blob_A"), BlobRef("blob_hidden")
    source = {"attachment": visible, "hidden_attachment": hidden}
    graph = AuthorizedResponseGraph({"attachment": visible}, (
        AuthorizedBlobSlot(("attachment",), "OrderItem", "20", "attachment", "tenant-a", 4, visible),))
    projected = []
    late = False

    class Authorizer:
        async def authorize(self, *_): return graph
    class Assembly:
        def principal(self, _): return ALICE
        async def snapshot(self, *_):
            return PreparedBoundDocument(replace(DOCUMENT,
                bindings=(replace(DOCUMENT.bindings[0], binding_version=4),)), 60)
    class Projector:
        async def project_batch(self, _context, authorized, ceiling):
            assert ceiling == deadline
            projected.extend(slot.reference.key for slot in authorized.blob_slots)
            return (ProjectedBlobURL("https://files.example.invalid/asset",
                deadline + timedelta(milliseconds=1) if late else deadline - timedelta(seconds=5)),)

    context = UserContext().insert_resource("response_graph_authorizer", Authorizer())
    context.insert_resource("blob_response_contributor", Projector())
    runtime(now=now).install(context, Assembly())
    options = ViewOptions("governed", "committed", now + timedelta(seconds=120))
    view = await ViewPreparationService().prepare(context, source, options)
    assert view.presentation == {"attachment": "https://files.example.invalid/asset"}
    assert view.expires_at == deadline - timedelta(seconds=5)
    assert projected == ["blob_A"] and source["hidden_attachment"] is hidden
    late = True
    with pytest.raises(ViewPreparationError) as failure:
        await ViewPreparationService().prepare(context, source, options)
    assert failure.value.code == "BLOB_SIGN_FAILED"
    assert failure.value.business_state == "committed" and failure.value.retry == "read"
    assert projected == ["blob_A", "blob_A"]
