"""#236: the Core transition helper is provider-independent and lossless."""
import pytest

from teaql.core import MutationVersionError, next_mutation_version
from teaql.core.mutation import DeleteCommand, MutationRequest, RecoverCommand, UpdateCommand


MAX = (1 << 63) - 1
MIN = -(1 << 63)


@pytest.mark.parametrize("operation,original,expected", [
    ("create", None, 1), ("update", 1, 2), ("update", MAX - 1, MAX),
    ("delete", 1, -2), ("delete", MAX, MIN), ("recover", -2, 3),
    ("recover", MIN + 2, MAX), ("hard_delete", MIN, MIN),
])
def test_core_version_exact_legal_endpoints(operation, original, expected):
    assert next_mutation_version(operation, original) == expected


@pytest.mark.parametrize("operation,version,code", [
    ("update", MAX, "VERSION_EXHAUSTED"), ("update", 0, "INVALID_VERSION_STATE"),
    ("update", -2, "INVALID_VERSION_STATE"), ("delete", -2, "INVALID_VERSION_STATE"),
    ("recover", MIN, "VERSION_EXHAUSTED"), ("recover", MIN + 1, "VERSION_EXHAUSTED"),
    ("recover", 1, "INVALID_VERSION_STATE"), ("update", MAX + 1, "INVALID_VERSION_STATE"),
    ("update", MIN - 1, "INVALID_VERSION_STATE"), ("update", True, "INVALID_VERSION_STATE"),
    ("update", 1.0, "INVALID_VERSION_STATE"), ("update", "PRIVATE_VERSION_VALUE", "INVALID_VERSION_STATE"),
])
def test_core_version_typed_errors_never_coerce_or_include_raw_input(operation, version, code):
    with pytest.raises(MutationVersionError) as caught:
        next_mutation_version(operation, version)
    assert caught.value.code == code and caught.value.operation == operation
    assert caught.value.original_version == version
    assert "PRIVATE_VERSION_VALUE" not in str(caught.value)


def test_core_request_validation_visits_the_entire_nested_batch_without_mutating_it():
    first = UpdateCommand.new("VersionProbe", 1).expected_version(1).value("name", "first")
    bad = RecoverCommand.new("VersionProbe", 2, MIN)
    request = MutationRequest.Batch([MutationRequest.Update(first, "valid first"),
        MutationRequest.Batch([MutationRequest.Recover(bad, "invalid last")], "nested")], "validate every member")
    with pytest.raises(MutationVersionError):
        request.validate()
    assert first.expected_version_val == 1 and first.values["name"].val == "first"
    assert bad.expected_version_val == MIN


def test_core_versionless_trusted_commands_keep_their_separate_role():
    MutationRequest.Update(UpdateCommand.new("VersionProbe", 1).value("name", "trusted"), "trusted update").validate()
    MutationRequest.Delete(DeleteCommand.new("VersionProbe", 1), "trusted live-only delete").validate()
    MutationRequest.Delete(DeleteCommand.new("VersionProbe", 1).expected_version(MIN).hard_delete(), "physical delete").validate()
