import csv
import re
from pathlib import Path

import pytest

from teaql.core import (
    BusinessIdEncodingKey,
    BusinessIdError,
    BusinessIdErrorCode,
    BusinessIdScope,
)
from teaql.runtime import (
    BUSINESS_ID_PERMUTATION_V1_DOMAIN_SIZE,
    encode_business_id_permutation_v1,
)


VECTOR = Path(__file__).parents[2] / "test-vectors" / "business-id-permutation-v1.csv"


def test_matches_every_cross_language_golden_vector() -> None:
    with VECTOR.open(newline="", encoding="utf-8") as input_file:
        rows = list(csv.DictReader(input_file))
    assert len(rows) == 10
    for row in rows:
        scope = BusinessIdScope(
            row["domain_root_key"],
            row["aggregate_type"],
            row["namespace"],
            row["period_key"],
        )
        key = BusinessIdEncodingKey(
            int(row["key_version"]), bytes.fromhex(row["key_hex"])
        )
        actual = encode_business_id_permutation_v1(int(row["sequence"]), scope, key)
        assert actual == row["expected_code"], row["case_id"]
        assert f"ORD-{row['period_key']}-{actual}" == row["expected_business_id"]


def test_is_deterministic_unique_and_canonical_for_retained_range() -> None:
    scope = BusinessIdScope("tenant-a", "commerce_order", "order_number", "20260925")
    key = BusinessIdEncodingKey(
        1,
        bytes.fromhex(
            "000102030405060708090a0b0c0d0e0f"
            "101112131415161718191a1b1c1d1e1f"
        ),
    )
    values: set[str] = set()
    for sequence in range(20_000):
        first = encode_business_id_permutation_v1(sequence, scope, key)
        after_restart = encode_business_id_permutation_v1(
            sequence,
            BusinessIdScope(
                "tenant-a", "commerce_order", "order_number", "20260925"
            ),
            BusinessIdEncodingKey(1, key.key),
        )
        assert first == after_restart
        assert re.fullmatch(r"[0-9A-Z]{6}", first)
        assert first not in values
        values.add(first)


def test_rejects_out_of_domain_sequence_and_malformed_definitions() -> None:
    scope = BusinessIdScope("tenant-a", "commerce_order", "order_number", "20260925")
    key = BusinessIdEncodingKey(1, bytes(32))
    for sequence in (-1, BUSINESS_ID_PERMUTATION_V1_DOMAIN_SIZE, True):
        with pytest.raises(BusinessIdError) as failure:
            encode_business_id_permutation_v1(sequence, scope, key)
        assert failure.value.code == BusinessIdErrorCode.RANGE_EXHAUSTED
    with pytest.raises(BusinessIdError):
        BusinessIdEncodingKey(0, bytes(32))
    with pytest.raises(BusinessIdError):
        BusinessIdEncodingKey(1, bytes(31))
    with pytest.raises(BusinessIdError):
        BusinessIdScope(" ", "commerce_order", "order_number", "20260925")
