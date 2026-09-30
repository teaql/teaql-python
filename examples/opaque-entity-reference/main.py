from datetime import datetime, timedelta, timezone

from teaql.runtime import AeadEntityReferenceCodec, EntityReferenceTokenError, UserContext


GOLDEN = "tqr1.AAAAAjMzMzMzMzMzMzMzM3bKiZgRSQQhfIj2cBXRDZIloUGHWLBp8QrXL_aejwIXPFtvV_E71O7wbOXy3cvYo_SwxvuS-89x572T9CO_pDAY4tbjWCNv"
now = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)
codec = AeadEntityReferenceCodec(
    2, {1: bytes([0x11]) * 32, 2: bytes([0x22]) * 32}
).with_clock(lambda: now).with_nonce_source(lambda: bytes([0x33]) * 12)
context = UserContext().with_entity_reference_codec(codec)

token = context.encode_entity_reference(
    "OrderItem", 42, 7, "edit-order", timedelta(hours=1)
)
assert token == GOLDEN
claims = context.decode_entity_reference(token, "OrderItem", "edit-order")
assert (claims.id, claims.version, claims.key_version) == (42, 7, 2)

try:
    context.decode_entity_reference(token, "OrderItem", "view-order")
    raise AssertionError("purpose substitution must fail")
except EntityReferenceTokenError as error:
    assert error.code == "ENTITY_REFERENCE_INVALID"

print("PASS: Python opaque entity reference")
