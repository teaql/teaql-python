import pytest
from teaql.core.mutation import InsertCommand, UpdateCommand, DeleteCommand
from teaql.core.value import Value

def test_insert_command_builder():
    cmd = InsertCommand.new("User").value("name", "Alice")
    assert cmd.entity == "User"
    assert cmd.values["name"] == Value.Text("Alice")

def test_update_command_builder():
    cmd = UpdateCommand.new("User", 1).with_expected_version(5).value("name", "Bob")
    assert cmd.entity == "User"
    assert cmd.id == Value.I64(1)
    assert cmd.expected_version == 5
    assert cmd.values["name"] == Value.Text("Bob")

def test_delete_command_builder():
    cmd = DeleteCommand.new("User", 1).with_expected_version(5).hard_delete()
    assert cmd.entity == "User"
    assert cmd.id == Value.I64(1)
    assert cmd.expected_version == 5
    assert cmd.soft_delete == False
