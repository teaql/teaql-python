from datetime import datetime, timezone

import pytest

from teaql_secure_document_reference import (
    ContextBoundReferenceRuntime, ReferenceDocumentScope, ReferenceIdentity,
    ReferenceKey, RoundTripReferenceError, StaticReferenceKeyProvider,
    TrustedReferencePrincipal,
)


VECTOR = ("tqr1.k2.MzMzMzMzMzMzMzMzmhCET15vBdSc1BbFJcrvMMnRP1wAyjunShYlFPnDZL7Gk5V1LuptWyrbiQ8LQSDHFUmN3o6vb-MEgXZuh3N-YkeO55CYLeVgiyBBYslzuSu-fvWC2KMZcnZ5D8BRmWpGYA2Ok5sWe1Fg1aIyadTjVoKB-H2vPW_0okj-")
ALICE = TrustedReferencePrincipal("oidc", "alice", "Platform", 7)
SCOPE = ReferenceDocumentScope("doc-100", "edit-order", "Order", 100, 9)
IDENTITY = ReferenceIdentity("OrderItem", 42, 3)
NOW = datetime(2026, 9, 27, tzinfo=timezone.utc)
KEYS = StaticReferenceKeyProvider("k2", (ReferenceKey("k1", bytes([0x11]) * 32),
                                          ReferenceKey("k2", bytes([0x22]) * 32)))


def runtime(*, now=NOW, allowed=True, environment="test-a"):
    def authorize(principal, _scope, identity):
        if not allowed or principal.subject != "alice" or identity.entity_type != "OrderItem" or identity.id != 42:
            raise PermissionError("denied")
    return ContextBoundReferenceRuntime("order-service", environment, KEYS, authorize,
                                        lambda: now, lambda: bytes([0x33]) * 12)


def code(call):
    with pytest.raises(RoundTripReferenceError) as error:
        call()
    return error.value.code


def test_tqr1_matches_rust_fixed_wire_vector_and_reauthorizes():
    assert runtime().issue(ALICE, SCOPE, IDENTITY, 600) == VECTOR
    resolved = runtime().consume(ALICE, SCOPE, VECTOR, "OrderItem")
    assert resolved.identity == IDENTITY
    assert resolved.key_id == "k2"
    assert resolved.issued_at == NOW
    assert resolved.expires_at == datetime(2026, 9, 27, 0, 10, tzinfo=timezone.utc)
    assert code(lambda: runtime(allowed=False).consume(ALICE, SCOPE, VECTOR, "OrderItem")) == \
        "ROUND_TRIP_REFERENCE_AUTHORIZATION_REQUIRED"


def test_tqr1_rejects_wrong_identity_scope_environment_and_expiry():
    assert code(lambda: runtime().consume(TrustedReferencePrincipal("oidc", "bob", "Platform", 7),
                                          SCOPE, VECTOR, "OrderItem")) == \
        "ROUND_TRIP_REFERENCE_SCOPE_MISMATCH"
    assert code(lambda: runtime().consume(ALICE,
                                          ReferenceDocumentScope("other", "edit-order", "Order", 100, 9),
                                          VECTOR, "OrderItem")) == "ROUND_TRIP_REFERENCE_SCOPE_MISMATCH"
    assert code(lambda: runtime().consume(ALICE,
                                          ReferenceDocumentScope("doc-100", "view-order", "Order", 100, 9),
                                          VECTOR, "OrderItem")) == "ROUND_TRIP_REFERENCE_INVALID"
    assert code(lambda: runtime(environment="other").consume(ALICE, SCOPE, VECTOR, "OrderItem")) == \
        "ROUND_TRIP_REFERENCE_INVALID"
    assert code(lambda: runtime().consume(ALICE, SCOPE, VECTOR, "Order")) == \
        "ROUND_TRIP_REFERENCE_SCOPE_MISMATCH"
    assert code(lambda: runtime(now=datetime(2026, 9, 27, 0, 10, tzinfo=timezone.utc)).consume(
        ALICE, SCOPE, VECTOR, "OrderItem")) == "ROUND_TRIP_REFERENCE_EXPIRED"


def test_tqr1_rejects_tamper_raw_id_noncanonical_and_bad_config():
    assert code(lambda: runtime().consume(ALICE, SCOPE, VECTOR[:-1] + "a", "OrderItem")) == \
        "ROUND_TRIP_REFERENCE_INVALID"
    assert code(lambda: runtime().consume(ALICE, SCOPE, "42", "OrderItem")) == \
        "ROUND_TRIP_REFERENCE_INVALID"
    assert code(lambda: runtime().consume(ALICE, SCOPE, VECTOR + "=", "OrderItem")) == \
        "ROUND_TRIP_REFERENCE_INVALID"
    assert code(lambda: runtime().issue(ALICE, SCOPE, ReferenceIdentity("OrderItem", 0, 3), 600)) == \
        "ROUND_TRIP_REFERENCE_INVALID"
    assert code(lambda: runtime().issue(ALICE, SCOPE, IDENTITY, 0)) == \
        "ROUND_TRIP_REFERENCE_INVALID"
    assert code(lambda: ReferenceKey("bad.key", bytes(32))) == \
        "ROUND_TRIP_REFERENCE_CONFIGURATION_INVALID"
