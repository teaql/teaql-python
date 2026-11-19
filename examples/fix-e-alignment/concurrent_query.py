"""Generated Q/E on one Context with two deliberately overlapping asyncio tasks.

The test observes real request owners and ordinary runtime SQL logs. It never
constructs trace nodes or installs a synthetic request scope. Context inspection
is a controlled verification boundary, not application API discovery.
"""
import argparse
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent / "generated"))
from E import E
from Q import Q
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.data_service import SQLiteTeaQLClient
from teaql.runtime import ContextEntityRef, FixedBusinessClock, UserContext
from partial_graph_loading import ObservedService


def nodes(values):
    return [dict(kind=n.kind, name=n.name, comment=n.comment or "") for n in values]


class OverlappingService(ObservedService):
    def __init__(self, service):
        super().__init__(service)
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.checkpoints = []

    async def query(self, context, request):
        if request.parent_request is None and request.intent.comment in ("alpha root", "beta root"):
            self.checkpoints.append((context, request, asyncio.current_task()))
            if len(self.checkpoints) == 2:
                self.entered.set()
            await self.release.wait()
        return await super().query(context, request)


async def main(database, round_number):
    assert round_number in (1, 2)
    assert database.is_absolute() and database.exists() == (round_number == 2)
    service = OverlappingService(SQLiteTeaQLClient(str(database)))
    context = (UserContext.new().install(GENERATED_RUNTIME_MODULE)
               .insert_resource("dataService", service)
               .with_business_clock(FixedBusinessClock(datetime(2032, 2, 29, 10, 15, 30, tzinfo=timezone.utc)))
               .with_active_root(ContextEntityRef("Tenant", 1)))
    ids, child_ids = {}, {}
    phones = dict(alpha="5550701", beta="5550702")
    try:
        await context.ensure_schema()
        for label in ("alpha", "beta"):
            order = ((await Q.purchase_orders().comment("Prepare " + label + " query fixture")
                     .purpose("Verify generated queries own independent intent").new_entity(context)))
            order.update_contact_phone(phones[label]).update_internal_note(None)
            child = ((await Q.order_items().comment("Prepare " + label + " child")
                     .purpose("Verify nested generated Q and loaded E").new_entity(context)))
            child.update_product_name(label + " child").update_unit_price(Decimal("1.00"))
            order.order_item_list().append(child)
            await order.audit_as("Seed " + label + " graph for request isolation").save(context)
            ids[label], child_ids[label] = order.id, child.id
            assert order.id > 0 and child.id > 0

        async def load(label, owner):
            return await (Q.purchase_orders().with_id_is(ids[owner])
                          .select_order_item_list_with(Q.order_items().limit(10).comment(label + " children"))
                          .limit(1).comment(label + " root").purpose(label + " purpose")
                          .execute_for_one(context))

        # Resolve any legitimate lazy provider setup before comparing Context
        # storage identities. This bounded Q query is not a concurrency result.
        await load("calibration", "alpha")
        service.calls.clear()
        context.clear_sql_logs()
        audits = []
        context.with_app_audit_event_sink(SimpleNamespace(on_safe_event=lambda _, event: audits.append(event)))
        context_before = {k: id(v) for k, v in vars(context).items()}
        resources_before = {k: id(v) for k, v in context._resources.items()}

        def context_unchanged():
            assert {k: id(v) for k, v in vars(context).items()} == context_before
            assert {k: id(v) for k, v in context._resources.items()} == resources_before
            return True

        tasks = [asyncio.create_task(load(label, label), name=label) for label in ("alpha", "beta")]
        ready = asyncio.create_task(service.entered.wait(), name="overlap-checkpoint")
        try:
            completed, _ = await asyncio.wait([ready, *tasks], timeout=5, return_when=asyncio.FIRST_COMPLETED)
            assert ready in completed, "both generated queries must reach the live checkpoint"
            assert len(service.checkpoints) == 2 and not any(task.done() for task in tasks)
            assert context.sql_logs() == [] and audits == []
            assert all(ctx is context for ctx, _, _ in service.checkpoints)
            a, b = [req for _, req, _ in service.checkpoints]
            assert a.root_request is not b.root_request
            # Observe the runtime's immutable invocation token as well as the
            # wrapper identity; no token is created or changed by this test.
            assert a._invocation_identity is not b._invocation_identity
            context_unchanged()
            checkpoints = [dict(comment=req.intent.comment, purpose=req.intent.purpose,
                                entity=req.request_name, root_is_self=req.root_request is req,
                                parent_absent=req.parent_request is None, task=task.get_name(),
                                nodes=nodes(req.business_trace_chain))
                           for _, req, task in service.checkpoints]
            service.release.set()
            result = await asyncio.wait_for(asyncio.gather(*tasks), timeout=10)
        finally:
            service.release.set()
            for task in [ready, *tasks]:
                if not task.done():
                    task.cancel()
            await asyncio.gather(ready, *tasks, return_exceptions=True)
        context_unchanged()
        after = await load("after", "alpha")
        context_unchanged()
        query_calls_before = service.calls.copy()
        logs_before = len(context.sql_logs())
        values = {}
        for label, row in zip(("alpha", "beta", "after"), [*result, after]):
            owner = "alpha" if label == "after" else label
            assert row is not None
            value = dict(id=row.id, phone=E.purchase_order(row).contact_phone().eval(),
                         count=E.purchase_order(row).order_item_list().size().eval(),
                         product=E.purchase_order(row).order_item_list().first().product_name().eval())
            assert value == dict(id=ids[owner], phone=phones[owner], count=1, product=owner + " child")
            values[label] = value
        assert service.calls == query_calls_before and len(context.sql_logs()) == logs_before
        events = [dict(operation=entry.operation.name, comment=entry.comment, purpose=entry.purpose,
                       outcome=entry.execution_outcome, result_count=entry.result_count, sql=entry.sql,
                       business=nodes(entry.trace_chain), physical=nodes(entry.trace_path))
                  for entry in context.sql_logs()]
        frame = dict(language="python", round=round_number, overlap_entered=2, same_context=True,
                     distinct_roots=True, distinct_invocations=True, context_storage_unchanged=context_unchanged(),
                     checkpoints=checkpoints, ids=ids, child_ids=child_ids, values=values, events=events,
                     provider_calls=dict(service.calls), e_provider_reads=0, e_sql_reads=0, audit_events=len(audits))
        print("PYTHON_CONCURRENT_QUERY_OBSERVATION=" + json.dumps(frame, sort_keys=True), flush=True)
        assert len(events) == 6 and not audits
        # The wrapper sees three root Q invocations; SQLite recursively executes
        # each child internally. Physical statement counts come from SQL logs.
        assert dict(service.calls) == {"query": 3}
        entity = checkpoints[0]["entity"]
        for label in ("alpha", "beta", "after"):
            own = [e for e in events if e["purpose"] == label + " purpose"]
            assert len(own) == 2
            for depth, event in enumerate(own):
                assert event["outcome"] == "success" and event["result_count"] == 1
                assert [n["kind"] for n in event["physical"]] == ["operation", "request", *(["relation"] if depth else []), "provider", "sql"]
                assert event["physical"][0]["name"] == event["physical"][1]["name"] == entity
                assert event["physical"][-2]["name"] == "sqlite" and event["physical"][-1]["name"] == "select"
                expected = [label + " purpose", label + " root"]
                if depth:
                    expected += ["select_order_item_list_with(...)", label + " children"]
                assert [n["comment"] for n in event["business"]] == expected
        frame["passed"] = True
        print("PYTHON_CONCURRENT_QUERY=" + json.dumps(frame, sort_keys=True), flush=True)
    finally:
        await service.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--round", type=int, required=True)
    args = parser.parse_args()
    asyncio.run(main(args.database.resolve(), args.round))
