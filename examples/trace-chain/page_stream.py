"""Current Assist -> generated Q/E/save -> observed real SQLite pages/cursors."""
import asyncio
import copy
import json
import os
import uuid

from E import E
from Q import Q
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.core.entity import EntityKey
from teaql.provider.sqlite import create_sqlite_service
from teaql.runtime import UserContext
from teaql.runtime.mutation_policy import (
    DelegatingMutationPolicyRegistry, MutationDecision, MutationPolicyIdentity,
)

from main import AuditSink, reset, scalar
from shared_reference import SharedService, assert_writes, load, pending, seed


class PageStreamService(SharedService):
    def __init__(self, service):
        super().__init__(service)
        self.count_pause = None
        self.active_cursors = set()
        self.opened_cursors = 0
        self.closed_cursors = 0
        self.active_driver_cursors = set()
        self.closed_driver_cursors = 0
        original_stream_sql = service.transport.stream_sql
        def observed_driver_sql(compiled, chunk_size):
            inner = original_stream_sql(compiled, chunk_size)
            token = object()
            async def rows():
                try:
                    async for batch in inner:
                        self.active_driver_cursors.add(token)
                        assert inner.ag_frame is not None
                        yield batch
                finally:
                    try:
                        await inner.aclose()
                    finally:
                        self.active_driver_cursors.discard(token)
                        self.closed_driver_cursors += 1
            return rows()
        service.transport.stream_sql = observed_driver_sql

    async def query(self, context, request):
        result = await super().query(context, request)
        if self.count_pause and request.query.aggregates:
            entered, release = self.count_pause
            self.count_pause = None
            entered.set()
            await asyncio.wait_for(release.wait(), 10)
        return result

    def query_stream(self, context, request, chunk_size):
        inner = self.service.query_stream(context, request, chunk_size)
        token = object()
        async def observed():
            self.opened_cursors += 1
            self.active_cursors.add(token)
            try:
                async for chunk in inner:
                    yield chunk
            finally:
                try:
                    await inner.aclose()
                finally:
                    self.active_cursors.remove(token)
                    self.closed_cursors += 1
        return observed()


class RecordingPolicy:
    identity = MutationPolicyIdentity('page-stream-example', '1', 'page-stream-v1')

    def __init__(self):
        self.plans = []

    def review(self, context, plan):
        self.plans.append(plan)
        return MutationDecision.allowed()


def log_row(entry):
    return {'comment': entry.comment, 'purpose': entry.purpose,
            'outcome': entry.execution_outcome, 'sql': entry.sql,
            'debugSQL': entry.debug_sql, 'count': entry.result_count,
            'path': [(n.kind, n.name, n.entity_id, n.comment) for n in entry.trace_path],
            'lineage': [(n.kind, n.name, n.entity_id, n.comment) for n in entry.mutation_lineage]}


def evidence(phase, service, sink, context, policy, **facts):
    print('PAGE_STREAM_OBSERVED ' + json.dumps({
        'phase': phase, 'facts': facts,
        'sql': [log_row(entry) for entry in context.sql_logs()],
        'commands': service.requests,
        'versions': service.versions[-len(service.requests):] if service.requests else [],
        'plans': [[{'entity': op.entity, 'id': scalar(op.entity_id),
                    'original_version': op.original_version,
                    'fields': sorted(op.changed_values)} for op in plan.operations] for plan in policy.plans],
        'audit': [(event.entity, scalar(event.entity_id),
                   [(n.kind, n.name, n.entity_id, n.comment) for n in event.trace_chain]) for event in sink.events],
    }))


def clear(service, sink, context, policy):
    reset(service, sink, context)
    policy.plans.clear()


async def pages(context, platform, service, sink, policy):
    seeded = [await seed(context, platform) for _ in range(3)]
    ids = [E.customer_order(row).id().eval() for row in seeded]
    revised = await load(context, ids[1])
    await revised.update_description('prior page revision').audit_as('advance paged root').save(context)
    builder = (Q.customer_orders().with_id_in(*ids).order_by_id_ascending()
        .select_platform_with(Q.platforms().limit(1))
        .select_order_item_list_with(Q.order_items().limit(10)).limit(3))
    executable = builder.comment('load independent page graphs').purpose('verify page mutation boundaries')
    entered, release = asyncio.Event(), asyncio.Event()
    service.count_pause = (entered, release)
    service.reuse_platform = True
    clear(service, sink, context, policy)
    task = asyncio.create_task(executable.execute_for_page(context, 1, 2))
    await asyncio.wait_for(entered.wait(), 10)
    builder.with_id_is(9223372036854775807).comment('LATE-PAGE-COMMENT').purpose('LATE-PAGE-PURPOSE')
    release.set()
    page = await asyncio.wait_for(task, 10)
    service.reuse_platform = False
    first, second = page.data
    assert page.total_count == 3 and [E.customer_order(row).id().eval() for row in page.data] == ids[1:]
    assert [E.customer_order(row).version().eval() for row in page.data] == [2, 1]
    assert first._entity_root is not second._entity_root and service.snapshot_uses == 2
    assert all(not row._entity_root.has_pending(row._teaql_entity_key()) for row in page.data)
    assert service.requests == [] and policy.plans == [] and sink.events == []
    assert all(entry.comment == 'load independent page graphs' and entry.purpose == 'verify page mutation boundaries'
               for entry in context.sql_logs())
    assert sum('COUNT(' in entry.sql.upper() for entry in context.sql_logs()) == 1
    before = copy.deepcopy(service.platform_snapshot)
    evidence('page-rows', service, sink, context, policy, ids=ids, total=page.total_count, versions=[2, 1],
             independent_ledgers=True, actual_shared_provider_record=True)
    first.update_description('saved first paged root')
    second.update_description('saved second paged root')
    second_key = EntityKey('CustomerOrder', ids[2])
    for phase, row, expected_version in [('page-save-first', first, 2), ('page-save-second', second, 1)]:
        clear(service, sink, context, policy)
        await row.audit_as(phase).save(context)
        assert_writes(service, sink, context, 1)
        assert service.requests[0][0] == 'CustomerOrder' and service.versions[-1] == expected_version
        assert len(policy.plans) == 1 and len(policy.plans[0].operations) == 1
        assert policy.plans[0].operations[0].original_version == expected_version
        if row is first:
            assert pending(second._entity_root, second_key)
        assert service.platform_snapshot == before
        evidence(phase, service, sink, context, policy, id=E.customer_order(row).id().eval(),
                 second_pending=pending(second._entity_root, second_key))
    child = first.order_item_list()[0]
    child.update_name('only changed paged descendant').audit_as('repair page child')
    clear(service, sink, context, policy)
    await first.audit_as('save clean paged ancestor').save(context)
    assert_writes(service, sink, context, 1)
    assert service.requests[0][0] == 'OrderItem' and service.versions[-1] == 1
    assert len(policy.plans) == 1 and len(policy.plans[0].operations) == 1
    evidence('page-save-child', service, sink, context, policy, id=E.order_item(child).id().eval())
    reloaded = [await load(context, identity) for identity in ids]
    assert [E.customer_order(row).version().eval() for row in reloaded] == [1, 3, 2]
    assert [E.order_item(row.order_item_list()[0]).version().eval() for row in reloaded] == [1, 2, 1]
    return ids


async def count_privacy(context, service, sink, policy, ids):
    private = 'PAGE-CHILD-PRIVATE-' + uuid.uuid4().hex
    context.configure_audit_policy('OrderItem', ['name'])
    clear(service, sink, context, policy)
    page = await (Q.customer_orders().with_id_in(*ids)
        .select_order_item_list_with(Q.order_items().with_name_is(private).limit(1)).limit(3)
        .comment('inspect page referencing ' + private).purpose('count page referencing ' + private)
        .execute_for_page(context, 0, 2))
    assert page.total_count == 3
    logs = context.sql_logs()
    assert any('COUNT(' in entry.sql.upper() for entry in logs)
    assert all(private not in str(entry.comment) + str(entry.purpose) + entry.debug_sql for entry in logs)
    assert all('[REDACTED]' in entry.comment and '[REDACTED]' in entry.purpose for entry in logs)
    evidence('page-count-privacy', service, sink, context, policy, total=3, canary_absent=True)
    clear(service, sink, context, policy)
    await Q.customer_orders().with_id_is(ids[0]).limit(1).comment(
        'independent intent ' + private).purpose('no ambient privacy').execute_for_list(context)
    assert context.sql_logs()[0].comment.endswith(private)
    evidence('page-independent-privacy', service, sink, context, policy, no_ambient_privacy=True)


async def streams(context, service, sink, policy, ids):
    clear(service, sink, context, policy)
    policy_calls = []
    context.with_request_policy(lambda query: policy_calls.append(query.entity))
    builder = Q.customer_orders().with_id_in(*ids).order_by_id_ascending().limit(3)
    stream = builder.comment('first captured stream').purpose('verify delayed scalar rows').execute_for_stream(context, chunk_size=1)
    other = (Q.customer_orders().with_id_in(*ids).order_by_id_ascending().limit(3).comment('second captured stream')
             .purpose('verify overlapping cursor intent').execute_for_stream(context, chunk_size=1))
    assert policy_calls == ['CustomerOrder', 'CustomerOrder'] and service.active_cursors == set()
    builder.with_id_is(9223372036854775807).comment('LATE-STREAM-COMMENT').purpose('LATE-STREAM-PURPOSE')
    first, other_first = await anext(stream), await anext(other)
    assert len(service.active_cursors) == 2 and context._graph_session is None
    assert len(service.active_driver_cursors) == 2
    assert context._audit_journal is None
    await Q.customer_orders().with_id_is(ids[0]).limit(1).comment('independent live query').purpose(
        'no ambient stream intent').execute_for_one(context)
    assert len(service.active_cursors) == 2
    assert len(service.active_driver_cursors) == 2
    await other.aclose()
    remaining = [row async for row in stream]
    await stream.aclose()
    rows = [first, *remaining]
    assert [E.customer_order(row).id().eval() for row in rows] == ids
    assert E.customer_order(other_first).id().eval() == ids[0]
    assert len({id(row._entity_root) for row in rows}) == 3
    assert service.active_cursors == set() and service.opened_cursors == service.closed_cursors == 2
    assert service.active_driver_cursors == set() and service.closed_driver_cursors == 2
    by_comment = {entry.comment: entry for entry in context.sql_logs()}
    assert set(by_comment) == {'first captured stream', 'second captured stream', 'independent live query'}
    assert by_comment['first captured stream'].result_count == 3
    assert by_comment['first captured stream'].execution_outcome == 'success'
    assert by_comment['second captured stream'].execution_outcome == 'cancelled'
    assert by_comment['second captured stream'].result_count == 1
    assert all(entry.trace_path[0].name == 'CustomerOrder' for entry in context.sql_logs())
    evidence('streams-overlap', service, sink, context, policy, ids=ids, two_live_cursors=True,
             two_live_driver_cursors=True, closed_driver_cursors=service.closed_driver_cursors,
             opened=service.opened_cursors, closed=service.closed_cursors, independent_ledgers=True)
    rows[0].update_description('saved streamed root')
    rows[1].update_description('pending streamed root')
    key = EntityKey('CustomerOrder', ids[1])
    clear(service, sink, context, policy)
    await rows[0].audit_as('save one streamed row').save(context)
    assert_writes(service, sink, context, 1)
    assert pending(rows[1]._entity_root, key) and service.requests[0][:2] == ('CustomerOrder', ids[0])
    assert len(policy.plans) == 1 and len(policy.plans[0].operations) == 1
    evidence('stream-save-one', service, sink, context, policy, id=ids[0], untouched_pending_id=ids[1])
    persisted = await load(context, ids[1])
    assert E.customer_order(persisted).description().eval() != 'pending streamed root'


async def main():
    context = UserContext.new().install(GENERATED_RUNTIME_MODULE)
    service = PageStreamService(create_sqlite_service(os.environ['TEAQL_TRACE_CHAIN_PAGE_STREAM_DB']))
    sink, policy = AuditSink(service), RecordingPolicy()
    context.insert_resource('dataService', service).with_app_audit_event_sink(sink)
    context.with_mutation_policy_registry(DelegatingMutationPolicyRegistry(lambda _: policy))
    context.set_diagnostic_sql_log_sink(type('Silent', (), {'write': lambda self, entry: None})())
    await context.ensure_schema()
    platform = await Q.platforms().with_id_is(1).limit(1).comment('reuse root for pages').purpose(
        'attach generated page fixtures').execute_for_one(context)
    ids = await pages(context, platform, service, sink, policy)
    await count_privacy(context, service, sink, policy, ids)
    await streams(context, service, sink, policy, ids)
    print('PASS: Python generated page/stream 8 phases, real SQL/plans/audit, explicit cursor close')


if __name__ == '__main__':
    asyncio.run(main())
