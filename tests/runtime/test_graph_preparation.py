"""#236: pure checks precede ID reservation and transaction admission."""
import asyncio
from datetime import datetime, timezone

import pytest

from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.mutation import InsertCommand
from teaql.core.value import DataType, Value
from teaql.runtime import CheckException, CheckResult, RuntimeModule, UserContext


class Provider:
    def __init__(self, events):
        self.events = events

    async def begin(self, context):
        self.events.append("begin")
        return self

    async def commit(self, context):
        self.events.append("commit")

    async def rollback(self, context):
        self.events.append("rollback")


def fixture():
    events = []
    provider = Provider(events)
    return UserContext().insert_resource("dataService", provider), provider, events


@pytest.mark.asyncio
async def test_rejected_preparation_never_enters_work_or_provider_and_releases_owner():
    context, provider, events = fixture()
    retained = []
    async def prepare(graph):
        retained.append(graph)
        graph.after_rollback(lambda: events.append("prepare cleanup"))
        raise ValueError("invalid input")
    async def work(graph):
        raise AssertionError("rejected preparation entered work")
    with pytest.raises(ValueError, match="invalid input"):
        await context.execute_graph_save(work, prepare=prepare, comment="reject input")
    assert events == ["prepare cleanup"]
    assert context._graph_save_guard.get() is None and not context._graph_save_lock.locked()
    assert context.get_resource("fix_time") is None
    assert context.require_resource("dataService") is provider
    with pytest.raises(RuntimeError, match="no longer writable"):
        retained[0]._require_active()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [None, "begin", "work", "commit"])
async def test_preparation_clock_and_custom_context_survive_transaction_binding(failure):
    context, provider, events = fixture()
    instant = datetime(2032, 2, 29, tzinfo=timezone.utc)
    reads, retained = [], []
    class Clock:
        def now(self):
            reads.append(1)
            return instant
    class CustomContext(UserContext):
        def customer_value(self):
            return "configured customer behavior"
    context = CustomContext().insert_resource("dataService", provider).with_business_clock(Clock())
    original_begin, original_commit = provider.begin, provider.commit
    async def begin(current):
        if failure == "begin":
            events.append("begin")
            raise ValueError("begin failed")
        return await original_begin(current)
    async def commit(current):
        await original_commit(current)
        if failure == "commit":
            raise ValueError("commit failed")
    provider.begin, provider.commit = begin, commit
    async def prepare(graph):
        retained.append(graph)
        assert type(graph.context) is CustomContext
        assert graph.context.customer_value() == "configured customer behavior"
        assert graph.context.require_resource("fix_time") is instant
        events.append("prepare")
    async def work(graph):
        assert graph is retained[0]
        assert graph.context.require_resource("fix_time") is instant
        assert graph.context.require_resource("dataService") is provider
        events.append("work")
        if failure == "work":
            raise ValueError("work failed")
        graph.after_commit(lambda: events.append("completion"))
        return 42
    if failure:
        with pytest.raises(ValueError, match=failure + " failed"):
            await context.execute_graph_save(work, prepare=prepare, comment="prepare one graph")
    else:
        assert await context.execute_graph_save(work, prepare=prepare, comment="prepare one graph") == 42
    expected = {None: ["prepare", "begin", "work", "commit", "completion"],
                "begin": ["prepare", "begin"], "work": ["prepare", "begin", "work", "rollback"],
                "commit": ["prepare", "begin", "work", "commit", "rollback"]}
    assert events == expected[failure] and reads == [1]
    assert context._graph_save_guard.get() is None and not context._graph_save_lock.locked()
    assert not retained[0]._active


@pytest.mark.asyncio
async def test_cancel_preparation_cleans_state_and_same_context_can_retry():
    context, _, events = fixture()
    entered, release = asyncio.Event(), asyncio.Event()
    async def prepare(graph):
        graph.after_rollback(lambda: events.append("cancel cleanup"))
        entered.set()
        await release.wait()
    async def work(graph):
        return "saved"
    task = asyncio.create_task(context.execute_graph_save(work, prepare=prepare, comment="cancel preparation"))
    try:
        await asyncio.wait_for(entered.wait(), 2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    finally:
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    assert events == ["cancel cleanup"]
    assert await context.execute_graph_save(work, comment="retry after cancellation") == "saved"
    assert events == ["cancel cleanup", "begin", "commit"]


@pytest.mark.asyncio
async def test_preparation_cannot_reenter_an_independent_root_or_execute_mutations():
    context, _, events = fixture()
    async def prepare(graph):
        with pytest.raises(RuntimeError, match="re-enter"):
            await context.execute_graph_save(work, comment="illegal root")
        async def child_task():
            with pytest.raises(RuntimeError, match="re-enter"):
                await context.execute_graph_save(work, comment="illegal spawned root")
        await asyncio.create_task(child_task())
        with pytest.raises(RuntimeError, match="preparation"):
            graph.context._require_mutation_invocation()
        events.append("prepared")
    async def work(graph):
        graph.context._require_mutation_invocation()
    await context.execute_graph_save(work, prepare=prepare, comment="explicit preparation owner")
    assert events == ["prepared", "begin", "commit"]


@pytest.mark.asyncio
async def test_concurrent_independent_saves_serialize_their_entire_preparation():
    context, _, events = fixture()
    entered, release, second_started = asyncio.Event(), asyncio.Event(), asyncio.Event()
    async def first_prepare(graph):
        events.append("prepare first")
        entered.set()
        await release.wait()
    async def second_prepare(graph):
        events.append("prepare second")
    async def work(graph):
        return graph
    first = asyncio.create_task(context.execute_graph_save(work, prepare=first_prepare, comment="first independent graph"))
    second = None
    try:
        await asyncio.wait_for(entered.wait(), 2)
        async def run_second():
            second_started.set()
            return await context.execute_graph_save(work, prepare=second_prepare, comment="second independent graph")
        second = asyncio.create_task(run_second())
        await asyncio.wait_for(second_started.wait(), 2)
        assert events == ["prepare first"]
        release.set()
        left, right = await asyncio.wait_for(asyncio.gather(first, second), 2)
        assert left is not right and left.context is not right.context
        assert left.context._mutation_policy is not right.context._mutation_policy
        assert events == ["prepare first", "begin", "commit", "prepare second", "begin", "commit"]
    finally:
        tasks = [task for task in (first, second) if task is not None]
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


@pytest.mark.asyncio
async def test_rejected_preparation_discards_queued_audit_and_reverse_cleans_callbacks():
    from teaql.runtime.audit import MutationAuditKind, RawAuditEvent
    context, _, events = fixture()
    class Sink:
        def on_safe_event(self, context, event):
            events.append("audit must not escape")
    context.with_app_audit_event_sink(Sink())
    async def prepare(graph):
        graph.after_rollback(lambda: events.append("parent cleanup"))
        graph.after_rollback(lambda: events.append("child cleanup"))
        await graph.context.send_audit_event(RawAuditEvent(MutationAuditKind.CREATED, "Probe", 1, ()))
        raise ValueError("preparation rejected")
    async def work(graph):
        raise AssertionError("rejected input entered work")
    with pytest.raises(ValueError, match="preparation rejected"):
        await context.execute_graph_save(work, prepare=prepare, comment="reject queued audit")
    assert events == ["child cleanup", "parent cleanup"]


@pytest.mark.asyncio
async def test_prepared_postcommit_failure_is_not_reported_as_rolled_back():
    context, _, events = fixture()
    async def prepare(graph):
        events.append("prepare")
    def broken():
        events.append("broken completion")
        raise ValueError("delivery failed")
    async def work(graph):
        graph.after_commit(broken)
        graph.after_commit(lambda: events.append("ledger cleanup"))
    with pytest.raises(RuntimeError) as caught:
        await context.execute_graph_save(work, prepare=prepare, comment="preserve committed outcome")
    assert caught.value.committed is True
    assert events == ["prepare", "begin", "commit", "broken completion", "ledger cleanup"]


@pytest.mark.asyncio
async def test_prepared_commands_are_invocation_owned_and_released():
    context, _, _ = fixture()
    owner, command, retained = object(), InsertCommand.new("Probe"), []
    async def prepare(graph):
        retained.append(graph)
        graph._remember_prepared_mutation(owner, "Create", command)
    async def work(graph):
        action, actual = graph._prepared_mutation(owner)
        assert action == "Create" and actual is command
        with pytest.raises(RuntimeError, match="not prepared"):
            graph._prepared_mutation(object())
    await context.execute_graph_save(work, prepare=prepare, comment="prepared command owner")
    assert retained[0]._prepared_mutations == {}
    async def another(graph):
        with pytest.raises(RuntimeError, match="not prepared"):
            graph._prepared_mutation(owner)
    await context.execute_graph_save(another, comment="independent next invocation")


@pytest.mark.asyncio
async def test_sealed_generated_empty_plan_never_opens_or_finishes_a_transaction():
    context, provider, events = fixture()
    retained = []
    async def prepare(graph):
        retained.append(graph)
        graph._seal_generated_plan()
        assert graph._empty_generated_plan
        with pytest.raises(RuntimeError, match='sealed'):
            graph._remember_prepared_mutation(object(), 'Update', object())
        with pytest.raises(RuntimeError, match='only be sealed once'):
            graph._seal_generated_plan()
    async def work(graph):
        assert graph.transaction is provider
        with pytest.raises(RuntimeError, match='sealed empty graph'):
            graph.context._require_mutation_invocation()
        events.append('unchanged view')
        return 17
    assert await context.execute_graph_save(work, prepare=prepare, comment='return unchanged generated graph') == 17
    assert events == ['unchanged view']
    assert not retained[0]._generated_plan_complete and retained[0]._prepared_mutations == {}
    assert context.require_resource('dataService') is provider
    assert context._graph_save_guard.get() is None and not context._graph_save_lock.locked()


@pytest.mark.asyncio
async def test_a_manual_empty_preparation_does_not_claim_complete_generated_traversal():
    context, _, events = fixture()
    async def prepare(graph):
        pass
    async def work(graph):
        assert not graph._empty_generated_plan
    await context.execute_graph_save(work, prepare=prepare, comment='preserve explicit manual transaction semantics')
    assert events == ['begin', 'commit']


@pytest.mark.asyncio
async def test_one_remaining_prepared_child_prevents_empty_plan_shortcut():
    context, _, events = fixture()
    owner = object()
    async def prepare(graph):
        graph._remember_prepared_mutation(owner, 'Update', InsertCommand.new('Child'))
        graph._seal_generated_plan()
        assert not graph._empty_generated_plan
    async def work(graph):
        assert graph._prepared_mutation(owner)[0] == 'Update'
        graph.context._require_mutation_invocation()
    await context.execute_graph_save(work, prepare=prepare, comment='an unchanged parent still has a changed child')
    assert events == ['begin', 'commit']


@pytest.mark.asyncio
async def test_failure_of_an_empty_generated_result_does_not_rollback_the_callers_provider():
    context, _, events = fixture()
    async def prepare(graph):
        graph.after_rollback(lambda: events.append('owned cleanup'))
        graph._seal_generated_plan()
    async def work(graph):
        raise ValueError('view traversal failed')
    with pytest.raises(ValueError, match='view traversal failed'):
        await context.execute_graph_save(work, prepare=prepare, comment='preserve an outer transaction on an empty plan')
    assert events == ['owned cleanup']
    async def retry(graph):
        return 42
    assert await context.execute_graph_save(retry, comment='retry an independent real transaction') == 42
    assert events == ['owned cleanup', 'begin', 'commit']


@pytest.mark.asyncio
async def test_generated_plan_cannot_be_sealed_outside_preparation():
    context, _, events = fixture()
    async def work(graph):
        with pytest.raises(RuntimeError, match='during preparation'):
            graph._seal_generated_plan()
    await context.execute_graph_save(work, comment='do not infer a complete graph from an arbitrary callback')
    assert events == ['begin', 'commit']


def test_deferred_fields_are_trusted_generated_insert_defaults_not_a_general_bypass():
    descriptor = (EntityDescriptor("Probe")
        .property(PropertyDescriptor("business_number").required().fixed_by_runtime(insert=True))
        .property(PropertyDescriptor("ordinary_input").required())
        .property(PropertyDescriptor("amount", DataType.F64)))
    class Checker:
        def check_and_fix(self, context, record, location, results):
            for field in ("business_number", "ordinary_input"):
                if field not in record:
                    results.append(CheckResult("required", field))
    context = RuntimeModule().schema_entity(descriptor).checker("Probe", Checker()).into_context()
    command = InsertCommand.new("Probe").value("ordinary_input", "ready")
    context._check_and_fix_mutation_input(command, deferred_fields=("business_number",))
    assert "business_number" not in command.values
    with pytest.raises(ValueError, match="generated insert default"):
        context._check_and_fix_mutation_input(command, deferred_fields=("ordinary_input",))
    with pytest.raises(CheckException) as caught:
        context.check_and_fix_mutation(command)
    assert caught.value.violations[0].location.model_path == "business_number"
    command.values["amount"] = Value.F64(float("nan"))
    with pytest.raises(CheckException) as caught:
        context._check_and_fix_mutation_input(command, deferred_fields=("business_number",))
    assert [item.location.model_path for item in caught.value.violations] == ["amount"]
