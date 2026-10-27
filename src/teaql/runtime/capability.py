"""Passive optional-module resource slots and explicit readiness checks."""

from __future__ import annotations

from inspect import isawaitable
from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from .context import UserContext


class RuntimeCapabilityResource(Protocol):
    @property
    def capability(self) -> str: ...

    def validate_ready(self, context: "UserContext") -> object: ...


def _slot(name: str) -> str:
    return f"teaql.runtime.capability:{name}"


def install_runtime_capability(context: "UserContext", resource: RuntimeCapabilityResource) -> None:
    name = getattr(resource, "capability", None)
    if not isinstance(name, str) or not name or name != name.strip() \
            or not callable(getattr(resource, "validate_ready", None)):
        raise ValueError("RUNTIME_CAPABILITY_INVALID")
    if context.get_resource(_slot(name)) is not None:
        raise ValueError("RUNTIME_CAPABILITY_DUPLICATE")
    context.insert_resource(_slot(name), resource)


async def validate_capabilities(context: "UserContext") -> None:
    for name in sorted(context._required_capabilities):
        resource = context.get_resource(_slot(name))
        if resource is None or getattr(resource, "capability", None) != name:
            raise RuntimeError(_missing(name))
        try:
            result = resource.validate_ready(context)
            if isawaitable(result):
                await result
        except Exception:
            raise RuntimeError(_missing(name)) from None


def _missing(name: str) -> str:
    return {"blob.v1": "BLOB_CAPABILITY_MISSING",
            "secure_document.v1": "DOCUMENT_CONFIGURATION"}.get(name, "RUNTIME_CAPABILITY_MISSING")
