from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol


class BusinessClock(Protocol):
    """Supplies time for domain behavior and Checker/Fix decisions."""

    def now(self) -> datetime:
        ...


class SystemBusinessClock:
    """Default context-owned clock backed by the UTC system clock."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


@dataclass(frozen=True)
class FixedBusinessClock:
    """Deterministic clock for tests and replay."""

    value: datetime

    def now(self) -> datetime:
        return self.value
