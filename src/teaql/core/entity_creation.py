"""Process-local creation provenance shared by generated entity plumbing.

These values are not JSON fields, authorization or a public creation API.
New entities must reserve their identity through the selected UserContext.
"""
from enum import Enum


class EntityCreationError(ValueError):
    code = "ENTITY_CREATION_CONTEXT_REQUIRED"

    def __init__(self):
        super().__init__(
            self.code + ": create through the generated Q factory and UserContext; "
            "hydrated mutations require a persisted identity and version")


def _positive_identity(value):
    return type(value) is int and 0 < value <= 18446744073709551615


class EntityCreationState(Enum):
    UNMANAGED = "unmanaged"
    RESERVED = "reserved"
    HYDRATED = "hydrated"

    def require_reserved(self, identity):
        if self is not EntityCreationState.RESERVED or not _positive_identity(identity):
            raise EntityCreationError()

    def validate_mutation(self, action, identity, persisted_version, pending):
        if not pending:
            return
        if action == "Create":
            self.require_reserved(identity)
        elif (action not in ("Update", "Delete") or self is not EntityCreationState.HYDRATED or not _positive_identity(identity)
              or type(persisted_version) is not int):
            raise EntityCreationError()
        # Persisted tombstones/exhausted values still have read provenance.
        # The shared version validator owns their precise lifecycle errors.
