"""#236: SQL optimistic versions stay inside the signed 64-bit lifecycle."""
import pytest

from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.mutation import DeleteCommand, RecoverCommand, UpdateCommand
from teaql.core.value import DataType
from teaql.provider.sqlite.dialect import SqliteDialect


MAX = (1 << 63) - 1
MIN = -(1 << 63)


def descriptor():
    return (EntityDescriptor("VersionProbe").table_name("version_probe")
            .property(PropertyDescriptor("id", DataType.I64).is_id())
            .property(PropertyDescriptor("version", DataType.I64).is_version())
            .property(PropertyDescriptor("name", DataType.Text)))


@pytest.mark.parametrize("version", [0, -1, MIN, MAX, MAX + 1, MIN - 1, True, 1.5, "1"])
def test_update_rejects_invalid_or_exhausted_original(version):
    command = UpdateCommand.new("VersionProbe", 1).expected_version(version).value("name", "pending")
    with pytest.raises(ValueError):
        SqliteDialect().compile_update(descriptor(), command)
    assert command.values["name"].val == "pending" and command.expected_version_val == version


@pytest.mark.parametrize("version", [0, -1, MIN, MAX + 1, MIN - 1, True, 1.5, "1"])
def test_soft_delete_rejects_nonlive_or_unrepresentable_original(version):
    with pytest.raises(ValueError):
        SqliteDialect().compile_delete(descriptor(), DeleteCommand.new("VersionProbe", 1).expected_version(version))


@pytest.mark.parametrize("version", [MIN, MIN + 1, MIN - 1])
def test_recover_rejects_unrepresentable_next_version(version):
    with pytest.raises(ValueError):
        SqliteDialect().compile_recover(descriptor(), RecoverCommand.new("VersionProbe", 1, version))


@pytest.mark.parametrize("operation,original,expected", [
    ("update", MAX - 1, MAX), ("delete", MAX, MIN), ("recover", MIN + 2, MAX),
    ("update", 1, 2), ("delete", 1, -2), ("recover", -2, 3),
])
def test_legal_endpoints_are_exact(operation, original, expected):
    dialect = SqliteDialect()
    if operation == "update":
        command = UpdateCommand.new("VersionProbe", 1).expected_version(original).value("name", "legal")
    elif operation == "delete":
        command = DeleteCommand.new("VersionProbe", 1).expected_version(original)
    else:
        command = RecoverCommand.new("VersionProbe", 1, original)
    compiled = getattr(dialect, "compile_" + operation)(descriptor(), command)
    assert any(type(value.val) is int and value.val == expected for value in compiled.params)
    assert compiled.params[-1].val == original


def test_blind_soft_delete_is_live_only_and_hard_delete_can_target_a_tombstone():
    dialect = SqliteDialect()
    blind = dialect.compile_delete(descriptor(), DeleteCommand.new("VersionProbe", 1))
    assert "version > 0" in blind.sql or '"version" > 0' in blind.sql
    hard = dialect.compile_delete(descriptor(), DeleteCommand.new("VersionProbe", 1).expected_version(MIN).hard_delete())
    assert hard.sql.startswith("DELETE FROM") and hard.params[-1].val == MIN
