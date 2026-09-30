"""Canonical TeaQL Business ID fixed-domain permutation profile V1."""

from __future__ import annotations

import hashlib
import hmac
import struct
import asyncio
from datetime import datetime
import re

from teaql.core.business_id import (
    BusinessIdAllocation,
    BusinessIdAllocator,
    BusinessIdDefinition,
    BusinessIdEncodingKey,
    BusinessIdError,
    BusinessIdErrorCode,
    BusinessIdGenerationRequest,
    BusinessIdKeyProvider,
    BusinessIdPlan,
    BusinessIdProfile,
    BusinessIdSlot,
    BusinessIdScope,
    BusinessIdValue,
)


BUSINESS_ID_PERMUTATION_V1_WIDTH = 6
BUSINESS_ID_PERMUTATION_V1_DOMAIN_SIZE = 2_176_782_336
BUSINESS_ID_PERMUTATION_V1_MAX_SEQUENCE = BUSINESS_ID_PERMUTATION_V1_DOMAIN_SIZE - 1
BUSINESS_ID_PERMUTATION_V1_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_MAGIC = b"teaql-business-id-fp-v1\0"


class InMemoryBusinessIdAllocator:
    """Single-process allocator for tests and development."""

    def __init__(self) -> None:
        self._counters: dict[BusinessIdScope, int] = {}
        self._lock = asyncio.Lock()

    async def allocate(self, plan: BusinessIdPlan) -> BusinessIdAllocation:
        async with self._lock:
            current = self._counters.get(plan.scope, plan.initial_sequence)
            if current > plan.maximum_sequence:
                raise BusinessIdError(
                    BusinessIdErrorCode.RANGE_EXHAUSTED,
                    f"Business ID range exhausted for {plan.scope.canonical_key()}",
                )
            self._counters[plan.scope] = current + 1
            return BusinessIdAllocation(plan.scope, current)


class StaticBusinessIdKeyProvider:
    def __init__(self, key: BusinessIdEncodingKey) -> None:
        self._key = key

    def current_key(self, context, definition, scope) -> BusinessIdEncodingKey:
        return self._key


class PermutedDailyBusinessIdProfile:
    def __init__(self, context, key_provider: BusinessIdKeyProvider) -> None:
        self._context = context
        self._key_provider = key_provider

    def plan(self, request: BusinessIdGenerationRequest) -> BusinessIdPlan:
        definition = request.definition
        if (
            definition.profile != BusinessIdDefinition.DEFAULT_PROFILE
            or definition.reset != "daily"
            or definition.date_format != BusinessIdDefinition.DEFAULT_DATE_FORMAT
            or definition.digits != BUSINESS_ID_PERMUTATION_V1_WIDTH
        ):
            raise BusinessIdError(
                BusinessIdErrorCode.DEFINITION_INVALID,
                "daily-permuted-v1 requires reset=daily, date_format=yyyyMMdd and digits=6",
            )
        date_text = request.business_date.strftime("%Y%m%d")
        scope = BusinessIdScope(
            request.domain_root_key,
            request.aggregate_type,
            definition.namespace,
            date_text,
        )
        return BusinessIdPlan(
            definition, scope, request.business_date, date_text, 0,
            BUSINESS_ID_PERMUTATION_V1_MAX_SEQUENCE,
        )

    def format(
        self, plan: BusinessIdPlan, allocation: BusinessIdAllocation
    ) -> BusinessIdValue:
        if allocation.scope != plan.scope:
            raise BusinessIdError(
                BusinessIdErrorCode.DEFINITION_INVALID,
                "Allocation scope does not match Business ID plan",
            )
        key = self._key_provider.current_key(
            self._context, plan.definition, plan.scope
        )
        if key is None:
            raise BusinessIdError(
                BusinessIdErrorCode.KEY_NOT_FOUND,
                "Business ID key provider returned no current key",
            )
        code = encode_business_id_permutation_v1(
            allocation.sequence, plan.scope, key
        )
        definition = plan.definition
        return BusinessIdValue(
            definition.separator.join((definition.prefix, plan.date_text, code)),
            definition.profile,
            definition.policy_version,
        )

    def validate(
        self, definition: BusinessIdDefinition, value: str
    ) -> BusinessIdValue:
        escaped = re.escape(definition.separator)
        pattern = re.compile(
            rf"^{re.escape(definition.prefix)}{escaped}(\d{{8}}){escaped}([0-9A-Z]{{6}})$"
        )
        match = pattern.fullmatch(value or "")
        if match is None:
            raise BusinessIdError(
                BusinessIdErrorCode.FORMAT_INVALID,
                f"Invalid daily-permuted-v1 Business ID: {value}",
            )
        try:
            datetime.strptime(match.group(1), "%Y%m%d")
        except ValueError as error:
            raise BusinessIdError(
                BusinessIdErrorCode.FORMAT_INVALID,
                f"Invalid daily-permuted-v1 Business ID: {value}",
            ) from error
        return BusinessIdValue(value, definition.profile, definition.policy_version)


class DefaultBusinessIdProfileFactory:
    def create(self, context, definition: BusinessIdDefinition) -> BusinessIdProfile:
        if definition.profile != BusinessIdDefinition.DEFAULT_PROFILE:
            raise BusinessIdError(
                BusinessIdErrorCode.PROFILE_NOT_FOUND,
                f"Business ID profile is not registered: {definition.profile}",
            )
        key_provider = context.get_resource("business_id_key_provider")
        if key_provider is None:
            raise BusinessIdError(
                BusinessIdErrorCode.KEY_NOT_FOUND,
                "Business ID key provider is not registered",
            )
        return PermutedDailyBusinessIdProfile(context, key_provider)


class DefaultBusinessIdService:
    def __init__(self, allocator: BusinessIdAllocator) -> None:
        self._allocator = allocator

    async def ensure(
        self,
        context,
        definition: BusinessIdDefinition,
        domain_root_key: str,
        aggregate_type: str,
        slot: BusinessIdSlot,
    ) -> BusinessIdValue:
        factory = context.get_resource("business_id_profile_factory")
        if factory is None:
            raise BusinessIdError(
                BusinessIdErrorCode.PROFILE_NOT_FOUND,
                "Business ID profile factory is not registered",
            )
        profile = factory.create(context, definition)
        current = slot.current_value()
        if current is not None and current.strip():
            return profile.validate(definition, current)
        if not slot.new_aggregate():
            raise BusinessIdError(
                BusinessIdErrorCode.IMMUTABLE,
                "An established Aggregate cannot be assigned a new Business ID",
            )
        plan = profile.plan(BusinessIdGenerationRequest(
            definition,
            domain_root_key,
            aggregate_type,
            context.business_date(),
        ))
        value = profile.format(plan, await self._allocator.allocate(plan))
        slot.assign_canonical_value(value.value)
        return value


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
