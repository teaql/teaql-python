from teaql.core.mutation import (
    TraceNode,
    InsertCommand as CoreInsertCommand,
    UpdateCommand as CoreUpdateCommand,
    DeleteCommand as CoreDeleteCommand,
    RecoverCommand as CoreRecoverCommand,
    MutationRequest
)
from teaql.core.value import Value
from teaql.data_service import DataServiceCapabilities

def test_mutation_request_trace_and_comment_accessors():
    trace1 = TraceNode(
        entity_type="User",
        entity_id=1,
        comment="Create User"
    )
    trace2 = TraceNode(
        entity_type="Profile",
        entity_id=None,
        comment="Create Profile"
    )
    trace_chain = [trace1, trace2]

    # Test Insert
    insert_cmd = CoreInsertCommand(
        entity="User",
        values={},
        trace_chain=trace_chain.copy()
    )
    req_insert = MutationRequest.Insert(insert_cmd)
    assert len(req_insert.trace_chain()) == 2
    assert req_insert.trace_chain()[1] == trace2
    assert req_insert.comment() == "Create Profile"

    # Test Update
    update_cmd = CoreUpdateCommand(
        entity="User",
        id=Value.from_any(1),
        values={},
        expected_version_val=None,
        old_values=None,
        trace_chain=trace_chain.copy()
    )
    req_update = MutationRequest.Update(update_cmd)
    assert len(req_update.trace_chain()) == 2
    assert req_update.comment() == "Create Profile"

    # Test Delete
    delete_cmd = CoreDeleteCommand(
        entity="User",
        id=Value.from_any(1),
        expected_version_val=None,
        soft_delete=True,
        trace_chain=trace_chain.copy()
    )
    req_delete = MutationRequest.Delete(delete_cmd)
    assert len(req_delete.trace_chain()) == 2
    assert req_delete.comment() == "Create Profile"

    # Test Recover
    recover_cmd = CoreRecoverCommand(
        entity="User",
        id=Value.from_any(1),
        expected_version_val=1,
        trace_chain=trace_chain.copy()
    )
    req_recover = MutationRequest.Recover(recover_cmd)
    assert len(req_recover.trace_chain()) == 2
    assert req_recover.comment() == "Create Profile"

    # Test Batch
    req_batch = MutationRequest.Batch([req_insert, req_update])
    assert len(req_batch.trace_chain()) == 0
    assert req_batch.comment() is None

    # Test empty trace chain
    insert_empty = CoreInsertCommand(
        entity="User",
        values={},
        trace_chain=[]
    )
    req_insert_empty = MutationRequest.Insert(insert_empty)
    assert req_insert_empty.comment() is None

def test_data_service_capabilities_default():
    caps = DataServiceCapabilities()
    assert caps.query is False
    assert caps.mutation is False
    assert caps.transaction is False
    assert caps.schema is False
    assert caps.id_generation is False
    assert caps.batch_mutation is False
    assert caps.returning is False

def test_query_request_coverage():
    from teaql.data_service import QueryRequest
    from teaql.core.query import SelectQuery
    q = QueryRequest(SelectQuery.new("User"))
    q.comment("c").purpose("p")
    assert q._comment == "c"
    assert q._purpose == "p"
    
    import pytest
    with pytest.raises(ValueError):
        q.comment("")
    with pytest.raises(ValueError):
        q.purpose("")
        
def test_aliases():
    from teaql.data_service import InsertCommand, UpdateCommand, DeleteCommand, RecoverCommand
    from teaql.core.mutation import InsertCommand as CoreInsertCommand
    assert InsertCommand(CoreInsertCommand.new("A")) is not None
    assert UpdateCommand(None) is not None
    assert DeleteCommand(None) is not None
    assert RecoverCommand(None) is not None
