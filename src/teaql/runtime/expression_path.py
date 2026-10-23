"""Value-free native E traces with canonical first-failure and complete-attempt locations."""
from __future__ import annotations

from dataclasses import dataclass, replace
import json

from .i18n import JsonFieldNamingProfile, ObjectLocation


@dataclass(frozen=True)
class ExpressionPath:
    root_expression: str
    profile: JsonFieldNamingProfile = JsonFieldNamingProfile.CAMEL_CASE
    location: ObjectLocation = ObjectLocation()
    steps: tuple[tuple[str, ObjectLocation], ...] = ()
    missing: int | None = None

    def member(self, name: str, method: str) -> ExpressionPath:
        return self._append(f"{method}()", self.location.property(name))

    def index(self, index: int, first: bool = False) -> ExpressionPath:
        return self._append("first()" if first else f"get({index})", self.location.index(index))

    def operation(self, call: str) -> ExpressionPath:
        return self._append(call, self.location)

    def _append(self, call: str, location: ObjectLocation) -> ExpressionPath:
        return replace(self, location=location, steps=self.steps + ((call, location),))

    def mark_missing(self) -> ExpressionPath:
        return self if self.missing is not None else replace(self, missing=len(self.steps) - 1)

    def with_failure_from(self, failed: ExpressionPath) -> ExpressionPath:
        return replace(self, missing=failed.missing)

    def render(self, broken: bool = False) -> str:
        return self.root_expression + "".join(
            f".{call}" + ("<broken>" if broken and index == self.missing else "")
            for index, (call, _) in enumerate(self.steps)
        )

    def diagnostic(self, fallback: str) -> dict:
        failure = self.location if self.missing is None else self.steps[self.missing][1]
        last = failure.segments[-1] if failure.segments else None
        location = self._wire_location(failure)
        return {
            "code": "NOT_LOADED",
            "location": location,
            "instancePath": failure.instance_path_for(self.profile),
            "breakPoint": last[1] if last and last[0] == "property" else fallback,
            "attemptedLocation": self._wire_location(self.location),
            "attemptedInstancePath": self.location.instance_path_for(self.profile),
            "breakPointIndex": max(0, len(failure.segments) - 1),
            "originalExpression": self.render(),
            "expressionWithBrokenPoint": self.render(True),
            "suggestedFix": {"action": "preload", "location": location},
        }

    @staticmethod
    def _wire_location(location: ObjectLocation) -> list[dict]:
        return [
            {"kind": kind, "index" if kind == "index" else "name": value}
            for kind, value in location.segments
        ]


class TeaQLNotLoadedError(RuntimeError):
    def __init__(self, path: ExpressionPath, break_point: str):
        self.path = path
        self.break_point = break_point
        super().__init__(json.dumps(self.to_wire(), ensure_ascii=False))

    @property
    def access_path(self) -> str:
        return self.path.location.model_path

    def with_path(self, path: ExpressionPath) -> TeaQLNotLoadedError:
        return TeaQLNotLoadedError(path.with_failure_from(self.path), self.break_point)

    def terminal(self, call: str) -> TeaQLNotLoadedError:
        return TeaQLNotLoadedError(self.path.operation(call), self.break_point)

    def to_wire(self) -> dict:
        return self.path.diagnostic(self.break_point)
