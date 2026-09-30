"""Canonical TeaQL Business ID fixed-domain permutation profile V1."""

from __future__ import annotations

import hashlib
import hmac
import struct

from teaql.core.business_id import (
    BusinessIdEncodingKey,
    BusinessIdError,
    BusinessIdErrorCode,
    BusinessIdScope,
)


BUSINESS_ID_PERMUTATION_V1_WIDTH = 6
BUSINESS_ID_PERMUTATION_V1_DOMAIN_SIZE = 2_176_782_336
BUSINESS_ID_PERMUTATION_V1_MAX_SEQUENCE = BUSINESS_ID_PERMUTATION_V1_DOMAIN_SIZE - 1
BUSINESS_ID_PERMUTATION_V1_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_MAGIC = b"teaql-business-id-fp-v1\0"


def encode_business_id_permutation_v1(
    sequence: int, scope: BusinessIdScope, key: BusinessIdEncodingKey
) -> str:
    if (
        not isinstance(sequence, int)
        or isinstance(sequence, bool)
        or sequence < 0
        or sequence >= BUSINESS_ID_PERMUTATION_V1_DOMAIN_SIZE
    ):
        raise BusinessIdError(
            BusinessIdErrorCode.RANGE_EXHAUSTED,
            f"Business ID V1 sequence must be in 0..{BUSINESS_ID_PERMUTATION_V1_MAX_SEQUENCE}",
        )
    if not isinstance(scope, BusinessIdScope) or not isinstance(key, BusinessIdEncodingKey):
        raise BusinessIdError(
            BusinessIdErrorCode.DEFINITION_INVALID,
            "Business ID V1 requires a BusinessIdScope and BusinessIdEncodingKey",
        )

    tweak = _canonical_tweak(scope, key.version)
    candidate = sequence
    while True:
        candidate = _permute32(candidate, tweak, key.key)
        if candidate < BUSINESS_ID_PERMUTATION_V1_DOMAIN_SIZE:
            break
    encoded = ["0"] * BUSINESS_ID_PERMUTATION_V1_WIDTH
    for index in range(BUSINESS_ID_PERMUTATION_V1_WIDTH - 1, -1, -1):
        encoded[index] = BUSINESS_ID_PERMUTATION_V1_ALPHABET[candidate % 36]
        candidate //= 36
    return "".join(encoded)


def _permute32(value: int, tweak: bytes, key: bytes) -> int:
    left = (value >> 16) & 0xFFFF
    right = value & 0xFFFF
    for round_number in range(8):
        digest = hmac.new(
            key, tweak + bytes((round_number,)) + struct.pack(">H", right), hashlib.sha256
        ).digest()
        output = struct.unpack_from(">H", digest)[0]
        left, right = right, (left ^ output) & 0xFFFF
    return (left << 16) | right


def _canonical_tweak(scope: BusinessIdScope, key_version: int) -> bytes:
    fields = (
        scope.domain_root_key,
        scope.aggregate_type,
        scope.namespace,
        scope.period_key,
    )
    framed = [_MAGIC, bytes((1,)), struct.pack(">I", key_version)]
    for value in fields:
        encoded = value.encode("utf-8")
        framed.extend((struct.pack(">I", len(encoded)), encoded))
    return b"".join(framed)
