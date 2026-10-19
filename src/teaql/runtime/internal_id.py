"""Trusted, context-owned internal ID allocation capability."""

from inspect import iscoroutinefunction
from typing import Protocol, runtime_checkable


@runtime_checkable
class InternalIdAllocator(Protocol):
    """Allocate unique per-entity IDs and reserve explicit-ID floors.

    Implementations used across processes must persist the floor. A failed
    transaction may leave gaps, but an allocated ID must never be reused.
    """

    async def next_id(self, entity: str) -> int: ...

    async def ensure_id_floor(self, entity: str, floor: int) -> None: ...


def validate_internal_id_allocator(allocator: InternalIdAllocator) -> InternalIdAllocator:
    """Reject incomplete/synchronous capabilities before provider execution."""
    if not isinstance(allocator, InternalIdAllocator):
        raise TypeError("internal ID allocator must provide next_id() and ensure_id_floor()")
    if not iscoroutinefunction(allocator.next_id) or not iscoroutinefunction(allocator.ensure_id_floor):
        raise TypeError("internal ID allocator methods must be async")
    return allocator
