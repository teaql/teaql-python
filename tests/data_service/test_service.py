from teaql.core.mutation import (
    TraceNode,
    InsertMutation as CoreInsertMutation,
    UpdateMutation as CoreUpdateMutation,
    DeleteMutation as CoreDeleteMutation,
    RecoverMutation as CoreRecoverMutation,
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
    insert_cmd = CoreInsertMutation(
        entity="User",
        values={},
        trace_chain=trace_chain.copy()
    )
    req_insert = MutationRequest.Insert(insert_cmd)
    assert len(req_insert.trace_chain()) == 2
    assert req_insert.trace_chain()[1] == trace2
    assert req_insert.comment() == "Create Profile"

    # Test Update
    update_cmd = CoreUpdateMutation(
        entity="User",
        id=Value.from_any(1),
        values={},
        expected_version=None,
        old_values=None,
        trace_chain=trace_chain.copy()
    )
    req_update = MutationRequest.Update(update_cmd)
    assert len(req_update.trace_chain()) == 2
    assert req_update.comment() == "Create Profile"

    # Test Delete
    delete_cmd = CoreDeleteMutation(
        entity="User",
        id=Value.from_any(1),
        expected_version=None,
        soft_delete=True,
        trace_chain=trace_chain.copy()
    )
    req_delete = MutationRequest.Delete(delete_cmd)
    assert len(req_delete.trace_chain()) == 2
    assert req_delete.comment() == "Create Profile"

    # Test Recover
    recover_cmd = CoreRecoverMutation(
        entity="User",
        id=Value.from_any(1),
        expected_version=1,
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
    insert_empty = CoreInsertMutation(
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
