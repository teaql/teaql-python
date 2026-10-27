"""Checked optimistic-version arithmetic shared by admission and SQL providers.

Python integers are unbounded; TeaQL versions deliberately are not. Arithmetic
must never turn a live update into a tombstone or recover an exhausted row.
"""
MIN_VERSION = -(1 << 63)
MAX_VERSION = (1 << 63) - 1


class MutationVersionError(ValueError):
    def __init__(self, code, operation, original_version):
        self.code = code
        self.operation = operation
        self.original_version = original_version
        super().__init__(f"{code}: invalid {operation} version transition")


def next_mutation_version(operation, original_version=None):
    operation = getattr(operation, "value", operation)
    if operation in ("create", "insert"):
        return 1
    if operation not in ("update", "delete", "recover", "hard_delete"):
        raise ValueError("unknown mutation version operation")
    if type(original_version) is not int or not MIN_VERSION <= original_version <= MAX_VERSION:
        raise MutationVersionError("INVALID_VERSION_STATE", operation, original_version)
    if operation == "hard_delete":
        return original_version  # Physical removal does not create a lifecycle version.
    if operation == "recover":
        if original_version >= 0:
            raise MutationVersionError("INVALID_VERSION_STATE", operation, original_version)
        if original_version < MIN_VERSION + 2:
            raise MutationVersionError("VERSION_EXHAUSTED", operation, original_version)
        return -original_version + 1
    if original_version <= 0:
        raise MutationVersionError("INVALID_VERSION_STATE", operation, original_version)
    if operation == "delete":
        return -original_version - 1
    if original_version == MAX_VERSION:
        raise MutationVersionError("VERSION_EXHAUSTED", operation, original_version)
    return original_version + 1


def validate_mutation_versions(data):
    """Pre-admit a complete request before its first hook or provider call.

Versionless trusted commands keep their separate role; SQL still restricts
blind soft deletion to live rows. A batch is fully visited before any Fix.
"""
    from .mutation import (BatchUpdateCommand, DeleteCommand, MutationRequest,
                           RecoverCommand, UpdateCommand)
    if isinstance(data, MutationRequest):
        validate_mutation_versions(data._data)
    elif isinstance(data, list):
        for child in data:
            validate_mutation_versions(child)
    elif isinstance(data, RecoverCommand):
        next_mutation_version("recover", data.expected_version_val)
    elif isinstance(data, (UpdateCommand, DeleteCommand)) and data.expected_version_val is not None:
        operation = ("update" if isinstance(data, UpdateCommand) else
                     "delete" if data.soft_delete else "hard_delete")
        next_mutation_version(operation, data.expected_version_val)
    elif isinstance(data, BatchUpdateCommand):
        for version in data.batch_expected_versions:
            if version is not None:
                next_mutation_version("update", version)
