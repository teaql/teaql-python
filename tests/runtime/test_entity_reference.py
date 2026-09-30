from datetime import datetime, timedelta, timezone

import pytest

from teaql.runtime import (
    AeadEntityReferenceCodec,
    EntityReferenceTokenError,
    UNSAFE_RAW_ENTITY_REFERENCES_ACKNOWLEDGEMENT,
    UNSAFE_RAW_ENTITY_REFERENCES_ENVIRONMENT,
    UserContext,
)


GOLDEN = "tqr1.AAAAAjMzMzMzMzMzMzMzM3bKiZgRSQQhfIj2cBXRDZIloUGHWLBp8QrXL_aejwIXPFtvV_E71O7wbOXy3cvYo_SwxvuS-89x572T9CO_pDAY4tbjWCNv"


def test_portable_codec_is_opaque_bound_rotatable_and_expiring():
    now = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)
    codec = AeadEntityReferenceCodec(
        2, {1: bytes([0x11]) * 32, 2: bytes([0x22]) * 32}
    ).with_clock(lambda: now).with_nonce_source(lambda: bytes([0x33]) * 12)

    token = codec.encode_entity_reference(
        "OrderItem", 42, 7, "edit-order", timedelta(hours=1)
    )
    assert token == GOLDEN
    assert "OrderItem" not in token
    claims = codec.decode_entity_reference(token, "OrderItem", "edit-order")
    assert (claims.id, claims.version, claims.key_version) == (42, 7, 2)

    old_codec = AeadEntityReferenceCodec(
        1, {1: bytes([0x11]) * 32}
    ).with_clock(lambda: now).with_nonce_source(lambda: bytes([0x44]) * 12)
    old_token = old_codec.encode_entity_reference(
        "OrderItem", 42, 7, "edit-order", timedelta(hours=1)
    )
    assert codec.decode_entity_reference(
        old_token, "OrderItem", "edit-order"
    ).key_version == 1

    for entity_type, purpose, candidate in (
        ("InvoiceItem", "edit-order", token),
        ("OrderItem", "other-purpose", token),
        ("OrderItem", "edit-order", token[:-1] + "A"),
    ):
        with pytest.raises(EntityReferenceTokenError, match="ENTITY_REFERENCE_INVALID"):
            codec.decode_entity_reference(candidate, entity_type, purpose)

    codec.with_clock(lambda: now + timedelta(hours=2))
    with pytest.raises(EntityReferenceTokenError, match="ENTITY_REFERENCE_INVALID"):
        codec.decode_entity_reference(token, "OrderItem", "edit-order")


def test_raw_references_require_exact_development_acknowledgement(monkeypatch):
    context = UserContext()
    monkeypatch.delenv(UNSAFE_RAW_ENTITY_REFERENCES_ENVIRONMENT, raising=False)
    with pytest.raises(EntityReferenceTokenError, match="ENTITY_REFERENCE_CODEC_REQUIRED"):
        context.encode_entity_reference("Order", 1, 1, "edit", timedelta(minutes=1))

    monkeypatch.setenv(
        UNSAFE_RAW_ENTITY_REFERENCES_ENVIRONMENT,
        UNSAFE_RAW_ENTITY_REFERENCES_ACKNOWLEDGEMENT,
    )
    token = context.encode_entity_reference(
        "Order", 1, 1, "edit", timedelta(minutes=1)
    )
    assert token.startswith("tqr0.")
    assert context.decode_entity_reference(token, "Order", "edit").id == 1
    with pytest.raises(EntityReferenceTokenError, match="ENTITY_REFERENCE_INVALID"):
        context.decode_entity_reference(token, "Order", "other-purpose")
