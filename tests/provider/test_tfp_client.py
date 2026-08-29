import json

import httpx
import pytest

from teaql.core.expr import Expr
from teaql.core.list import SmartList
from teaql.core.mutation import TraceNode, UpdateCommand
from teaql.core.query import SelectQuery, Slice
from teaql.data_service import MutationRequest, QueryRequest
from teaql.provider.tfp_client import (
    FederalMutation, FederalQuery, TeaQLFederalClient, TfpError, TfpHttpProvider,
    _reject_trusted_fields,
)


class RecordingTelemetry:
    def __init__(self):
        self.events = []

    def start(self, operation):
        event = {"operation": operation, "outcome": None}
        self.events.append(event)

        class Scope:
            def success(_, attributes=None):
                event["outcome"] = "success"
                event["attributes"] = attributes or {}

            def failure(_, error):
                event["outcome"] = "failure"
                event["error"] = error

        return Scope()

    def inject(self, carrier):
        carrier["traceparent"] = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"

    def flush(self):
        pass

    def shutdown(self):
        pass


@pytest.mark.asyncio
async def test_canonical_query_returns_smart_list_and_propagates_context():
    captured = {}

    async def handler(request):
        captured["request"] = request
        return httpx.Response(200, json={"data": [{"id": 7}], "facets": {"state": []}})

    telemetry = RecordingTelemetry()
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://tfp.test")
    client = TeaQLFederalClient("https://tfp.test", client=http, runtime_telemetry=telemetry)
    rows = await client.execute_query(FederalQuery(
        entity="CustomerOrder", filter_condition={"status": {"$eq": "NEW"}},
        limit=20, offset=0, order_items=[{"field": "id", "direction": "Desc"}],
        select_items=["id"], comment="List new orders", purpose="Render queue",
    ))

    assert isinstance(rows, SmartList)
    assert rows == [{"id": 7}]
    payload = json.loads(captured["request"].content)
    assert payload == {
        "entity": "CustomerOrder", "filterCondition": {"status": {"$eq": "NEW"}},
        "limitValue": 20, "offsetValue": 0,
        "orderItems": [{"field": "id", "direction": "Desc"}],
        "selectItems": ["id"], "groupByItems": [], "aggregateItems": [],
        "commentText": "List new orders", "purposeText": "Render queue",
    }
    assert captured["request"].headers["traceparent"].startswith("00-")
    assert telemetry.events[0]["operation"].name == "client.query"
    assert telemetry.events[0]["attributes"]["teaql.result.cardinality"] == 1


@pytest.mark.asyncio
async def test_mutation_serializes_audit_and_expected_version():
    captured = {}

    async def handler(request):
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"affectedRows": 1, "data": [{"id": 42}]})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://tfp.test")
    client = TeaQLFederalClient("https://tfp.test", client=http)
    result = await client.execute_mutation(FederalMutation(
        "CustomerOrder", "Update", {"status": "PAID"}, "Mark paid",
        id=42, expected_version=3,
    ))
    assert result["affectedRows"] == 1
    assert captured["payload"] == {
        "entity": "CustomerOrder", "action": "Update", "payload": {"status": "PAID"},
        "id": 42, "expectedVersion": 3, "comment": "Mark paid",
    }


@pytest.mark.asyncio
async def test_provider_adapts_core_query_and_mutation_without_broadening():
    payloads = []

    async def handler(request):
        payloads.append(json.loads(request.content))
        if request.url.path == "/query":
            return httpx.Response(200, json={"data": [{"id": 7}]})
        return httpx.Response(200, json={"affectedRows": 1, "data": [{"id": 42}]})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://tfp.test")
    provider = TfpHttpProvider("https://tfp.test", client=http)
    query = SelectQuery.new("CustomerOrder").filter(Expr.eq("status", "NEW"))
    query.slice = Slice(offset=0, limit=20)
    result = await provider.query(None, QueryRequest(query).comment("List orders").purpose("Render queue"))
    assert isinstance(result.rows, SmartList)
    assert payloads[0]["filterCondition"] == {"status": {"$eq": "NEW"}}

    command = UpdateCommand.new("CustomerOrder", 42).expected_version(3).value("status", "PAID")
    command.trace_chain.append(TraceNode(comment="Mark paid"))
    mutation = await provider.mutate(None, MutationRequest.Update(command))
    assert mutation.affected_rows == 1
    assert payloads[1]["expectedVersion"] == 3


@pytest.mark.asyncio
async def test_fails_closed_for_trusted_fields_errors_and_streaming():
    async def handler(_):
        return httpx.Response(403, json={"code": "TFP_FORBIDDEN_FIELD", "message": "denied"})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://tfp.test")
    client = TeaQLFederalClient("https://tfp.test", client=http)
    with pytest.raises(TfpError, match="TFP_FORBIDDEN_FIELD"):
        await client.execute_query(FederalQuery(
            "CustomerOrder", filter_condition={"tenantId": {"$eq": 9}},
            comment="attack", purpose="negative test",
        ))
    with pytest.raises(TfpError) as remote:
        await client.execute_query(FederalQuery(
            "CustomerOrder", comment="query", purpose="negative test",
        ))
    assert remote.value.code == "TFP_FORBIDDEN_FIELD"
    with pytest.raises(TfpError, match="dedicated protocol"):
        await client.execute_for_stream()
    with pytest.raises(TfpError, match="TFP_FORBIDDEN_FIELD"):
        _reject_trusted_fields({"idSetPagination": {"namespace": "attacker"}})
