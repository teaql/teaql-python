"""Durable SQL allocation for externally visible Business IDs."""

from __future__ import annotations

import asyncio
from datetime import datetime, time, timezone

from teaql.core.business_id import (
    BusinessIdAllocation,
    BusinessIdError,
    BusinessIdErrorCode,
    BusinessIdPlan,
)
from teaql.core.value import Value
from teaql.sql.types import CompiledQuery


class SqlBusinessIdAllocator:
    """Portable optimistic allocator. Schema installation remains explicit."""

    MAX_ATTEMPTS = 100

    def __init__(self, dialect, transport) -> None:
        self._dialect = dialect
        self._transport = transport

    async def allocate(self, plan: BusinessIdPlan) -> BusinessIdAllocation:
        scope_key = plan.scope.canonical_key()
        updated_at = int(datetime.combine(
            plan.business_date, time.min, tzinfo=timezone.utc
        ).timestamp() * 1000)
        placeholders = [self._dialect.placeholder(index) for index in range(1, 6)]
        last_conflict: Exception | None = None

        for _attempt in range(1, self.MAX_ATTEMPTS + 1):
            try:
                rows = await self._transport.fetch_all_sql(CompiledQuery(
                    "SELECT current_value, version FROM teaql_business_id_space "
                    f"WHERE scope_key = {placeholders[0]}",
                    [Value.from_any(scope_key)],
                ))
            except Exception as error:
                raise RuntimeError(
                    "Business ID allocation requires explicit ensure_schema() "
                    "and an accessible teaql_business_id_space table"
                ) from error
            if not rows:
                try:
                    changed, _ = await self._transport.execute_sql(CompiledQuery(
                        "INSERT INTO teaql_business_id_space "
                        "(scope_key, current_value, version, updated_at) VALUES "
                        f"({placeholders[0]}, {placeholders[1]}, 1, {placeholders[2]})",
                        [
                            Value.from_any(scope_key),
                            Value.from_any(plan.initial_sequence),
                            Value.from_any(updated_at),
                        ],
                    ))
                    if changed == 1:
                        return BusinessIdAllocation(
                            plan.scope, plan.initial_sequence
                        )
                    raise RuntimeError(
                        f"Business ID insert for {scope_key} changed {changed} rows"
                    )
                except Exception as error:
                    last_conflict = error
                    observed = await self._transport.fetch_all_sql(CompiledQuery(
                        "SELECT current_value, version FROM teaql_business_id_space "
                        f"WHERE scope_key = {placeholders[0]}",
                        [Value.from_any(scope_key)],
                    ))
                    if not observed:
                        raise RuntimeError(
                            "Business ID allocation requires explicit ensure_schema()"
                        ) from error
            else:
                current = int(rows[0]["current_value"])
                version = int(rows[0]["version"])
                if current < 0 or version < 1:
                    raise RuntimeError(
                        f"Invalid Business ID sequence row for {scope_key}"
                    )
                if current >= plan.maximum_sequence:
                    raise BusinessIdError(
                        BusinessIdErrorCode.RANGE_EXHAUSTED,
                        f"Business ID range exhausted for {scope_key}",
                    )
                next_value = current + 1
                changed, _ = await self._transport.execute_sql(CompiledQuery(
                    "UPDATE teaql_business_id_space SET current_value = "
                    f"{placeholders[0]}, version = version + 1, updated_at = {placeholders[1]} "
                    f"WHERE scope_key = {placeholders[2]} AND version = {placeholders[3]} "
                    f"AND current_value = {placeholders[4]}",
                    [
                        Value.from_any(next_value),
                        Value.from_any(updated_at),
                        Value.from_any(scope_key),
                        Value.from_any(version),
                        Value.from_any(current),
                    ],
                ))
                if changed == 1:
                    return BusinessIdAllocation(plan.scope, next_value)
                if changed != 0:
                    raise RuntimeError(
                        f"Business ID update for {scope_key} changed {changed} rows"
                    )
            await asyncio.sleep(0.001)

        raise BusinessIdError(
            BusinessIdErrorCode.ALLOCATION_RETRY_EXHAUSTED,
            f"Business ID allocation did not converge for {scope_key}: {last_conflict}",
        )
