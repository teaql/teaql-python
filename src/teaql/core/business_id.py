"""Portable core types for externally visible Aggregate-root Business IDs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from teaql.runtime.context import UserContext


class BusinessIdErrorCode(str, Enum):
    PROFILE_NOT_FOUND = "BUSINESS_ID_PROFILE_NOT_FOUND"
    DEFINITION_INVALID = "BUSINESS_ID_DEFINITION_INVALID"
    RANGE_EXHAUSTED = "BUSINESS_ID_RANGE_EXHAUSTED"
    ALLOCATION_RETRY_EXHAUSTED = "BUSINESS_ID_ALLOCATION_RETRY_EXHAUSTED"
    FORMAT_INVALID = "BUSINESS_ID_FORMAT_INVALID"
    DUPLICATE = "BUSINESS_ID_DUPLICATE"
    IMMUTABLE = "BUSINESS_ID_IMMUTABLE"
    KEY_NOT_FOUND = "BUSINESS_ID_KEY_NOT_FOUND"
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

    def canonical_key(self) -> str:
        def escape(value: str) -> str:
            return value.replace("%", "%25").replace("|", "%7C")

        return "|".join(escape(value) for value in (
            self.domain_root_key,
            self.aggregate_type,
            self.namespace,
            self.period_key,
        ))


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


@dataclass(frozen=True)
class BusinessIdDefinition:
    field_name: str
    profile: str
    prefix: str
    date_format: str
    reset: str
    digits: int
    separator: str
    namespace: str
    policy_version: int

    DEFAULT_PROFILE = "daily-permuted-v1"
    DEFAULT_DATE_FORMAT = "yyyyMMdd"
    DEFAULT_DIGITS = 6

    def __post_init__(self) -> None:
        for name in (
            "field_name", "profile", "prefix", "date_format", "reset",
            "separator", "namespace",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise BusinessIdError(
                    BusinessIdErrorCode.DEFINITION_INVALID,
                    f"{name} must not be blank",
                )
        if self.profile == self.DEFAULT_PROFILE and self.digits != self.DEFAULT_DIGITS:
            raise BusinessIdError(
                BusinessIdErrorCode.DEFINITION_INVALID,
                "daily-permuted-v1 requires exactly 6 digits",
            )
        if not isinstance(self.digits, int) or isinstance(self.digits, bool) or not 1 <= self.digits <= 18:
            raise BusinessIdError(
                BusinessIdErrorCode.DEFINITION_INVALID,
                "digits must be between 1 and 18",
            )
        if not isinstance(self.policy_version, int) or isinstance(self.policy_version, bool) or self.policy_version < 1:
            raise BusinessIdError(
                BusinessIdErrorCode.DEFINITION_INVALID,
                "policy_version must be positive",
            )

    @classmethod
    def daily_permuted(cls, field_name: str, prefix: str, namespace: str) -> "BusinessIdDefinition":
        return cls(
            field_name, cls.DEFAULT_PROFILE, prefix, cls.DEFAULT_DATE_FORMAT,
            "daily", cls.DEFAULT_DIGITS, "-", namespace, 1,
        )

    def maximum_sequence(self) -> int:
        if self.profile == self.DEFAULT_PROFILE:
            return 2_176_782_335
        return 10 ** self.digits - 1


@dataclass(frozen=True)
class BusinessIdGenerationRequest:
    definition: BusinessIdDefinition
    domain_root_key: str
    aggregate_type: str
    business_date: date


@dataclass(frozen=True)
class BusinessIdPlan:
    definition: BusinessIdDefinition
    scope: BusinessIdScope
    business_date: date
    date_text: str
    initial_sequence: int
    maximum_sequence: int

    def __post_init__(self) -> None:
        if self.initial_sequence < 0 or self.maximum_sequence < self.initial_sequence:
            raise BusinessIdError(
                BusinessIdErrorCode.DEFINITION_INVALID,
                "Business ID allocation range must satisfy 0 <= initial_sequence <= maximum_sequence",
            )


@dataclass(frozen=True)
class BusinessIdAllocation:
    scope: BusinessIdScope
    sequence: int


@dataclass(frozen=True)
class BusinessIdValue:
    value: str
    profile: str
    policy_version: int

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise BusinessIdError(
                BusinessIdErrorCode.FORMAT_INVALID,
                "Business ID value must not be blank",
            )


class BusinessIdSlot(Protocol):
    def current_value(self) -> str | None: ...
    def new_aggregate(self) -> bool: ...
    def assign_canonical_value(self, value: str) -> None: ...


class BusinessIdAllocator(Protocol):
    async def allocate(self, plan: BusinessIdPlan) -> BusinessIdAllocation: ...


class BusinessIdProfile(Protocol):
    def plan(self, request: BusinessIdGenerationRequest) -> BusinessIdPlan: ...
    def format(self, plan: BusinessIdPlan, allocation: BusinessIdAllocation) -> BusinessIdValue: ...
    def validate(self, definition: BusinessIdDefinition, value: str) -> BusinessIdValue: ...


class BusinessIdProfileFactory(Protocol):
    def create(self, context: "UserContext", definition: BusinessIdDefinition) -> BusinessIdProfile: ...


class BusinessIdKeyProvider(Protocol):
    def current_key(
        self,
        context: "UserContext",
        definition: BusinessIdDefinition,
        scope: BusinessIdScope,
    ) -> BusinessIdEncodingKey: ...


class BusinessIdService(Protocol):
    async def ensure(
        self,
        context: "UserContext",
        definition: BusinessIdDefinition,
        domain_root_key: str,
        aggregate_type: str,
        slot: BusinessIdSlot,
    ) -> BusinessIdValue: ...
