"""Portable core types for externally visible Aggregate-root Business IDs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BusinessIdErrorCode(str, Enum):
    DEFINITION_INVALID = "BUSINESS_ID_DEFINITION_INVALID"
    RANGE_EXHAUSTED = "BUSINESS_ID_RANGE_EXHAUSTED"
    ENCODING_FAILED = "BUSINESS_ID_ENCODING_FAILED"


class BusinessIdError(ValueError):
    def __init__(self, code: BusinessIdErrorCode, message: str):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class BusinessIdScope:
    domain_root_key: str
    aggregate_type: str
    namespace: str
    period_key: str

    def __post_init__(self) -> None:
        for name, value in (
            ("domain_root_key", self.domain_root_key),
            ("aggregate_type", self.aggregate_type),
            ("namespace", self.namespace),
            ("period_key", self.period_key),
        ):
            if not isinstance(value, str) or not value.strip():
                raise BusinessIdError(
                    BusinessIdErrorCode.DEFINITION_INVALID,
                    f"{name} must not be blank",
                )


@dataclass(frozen=True)
class BusinessIdEncodingKey:
    version: int
    key: bytes

    def __post_init__(self) -> None:
        if (
            not isinstance(self.version, int)
            or isinstance(self.version, bool)
            or not (1 <= self.version <= 0xFFFFFFFF)
        ):
            raise BusinessIdError(
                BusinessIdErrorCode.DEFINITION_INVALID,
                "Business ID key version must be a positive u32",
            )
        if (
            not isinstance(self.key, (bytes, bytearray, memoryview))
            or len(self.key) != 32
        ):
            raise BusinessIdError(
                BusinessIdErrorCode.DEFINITION_INVALID,
                "Business ID V1 key must contain exactly 32 bytes",
            )
        object.__setattr__(self, "key", bytes(self.key))
