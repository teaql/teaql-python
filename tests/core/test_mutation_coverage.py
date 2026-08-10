import pytest
from teaql.core.mutation import (
    InsertCommand, UpdateCommand, DeleteCommand, RecoverCommand, 
    BatchInsertCommand, BatchUpdateCommand, MutationRequest, TraceNode, MutationKind
)
from teaql.core.value import Value

def test_mutation_commands():
    t = TraceNode("User", 1, "comment")
    
    i = InsertCommand.new("User").value("name", "Alice")
    assert i.entity == "User"
    assert "name" in i.values
    
    u = UpdateCommand.new("User", 1).expected_version(1).value("name", "Bob")
    assert u.entity == "User"
    assert u.expected_version_val == 1
    assert "name" in u.values
    
    d = DeleteCommand.new("User", 1).expected_version(1).hard_delete()
    assert d.soft_delete is False
    
    r = RecoverCommand.new("User", 1, 1).expected_version(2)
    assert r.expected_version_val == 2
    
    bi = BatchInsertCommand.new("User")
    assert bi.entity == "User"
    
    bu = BatchUpdateCommand.new("User", ["name"])
    assert bu.entity == "User"
    assert "name" in bu.update_fields

def test_mutation_requests():
    t = TraceNode("User", 1, "test")
    i = InsertCommand.new("User")
    i.trace_chain = [t]
    
    req_i = MutationRequest.Insert(i)
    req_u = MutationRequest.Update(UpdateCommand.new("U", 1))
    req_d = MutationRequest.Delete(DeleteCommand.new("U", 1))
    req_r = MutationRequest.Recover(RecoverCommand.new("U", 1, 1))
    
    req_b = MutationRequest.Batch([req_i, req_u])
    
    assert len(req_i.trace_chain()) == 1
    assert req_i.comment() == "test"
    
    assert req_b.trace_chain() == []
    assert req_b.comment() is None
