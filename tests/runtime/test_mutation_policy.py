from datetime import datetime, timezone

import pytest

from teaql.core.mutation import InsertCommand, MutationRequest, TraceNode
from teaql.core.value import Value
from teaql.data_service import (
    DataServiceOperation,
    ExecutionMetadata,
    MutationResult,
)
from teaql.runtime import (
    MISSING_APPROVAL,
    MISSING_POLICY,
    DelegatingMutationPolicyApprovalProvider,
    DelegatingMutationPolicyRegistry,
    MutationDecision,
    MutationOperation,
    MutationOperationKind,
    MutationPlan,
    MutationPolicyApproval,
    MutationPolicyApprovalStatus,
    MutationPolicyError,
    MutationPolicyIdentity,
    MutationPolicySource,
    UserContext,
)
from teaql.runtime.audit import MutationAuditKind, RawAuditEvent
from teaql.sql.executor import SqlDataServiceExecutor


class TestPolicy:
    __test__ = False

    def __init__(self, identity, review):
        self.identity = identity
        self._review = review

    def review(self, context, plan):
        return self._review(plan)


class RecordingWarnings:
    def __init__(self, failure=None):
        self.events = []
        self.failure = failure

    def on_warning(self, context, warning):
        self.events.append(warning)
        if self.failure:
            raise self.failure


class RecordingAudit:
    def __init__(self):
        self.events = []

    async def on_safe_event(self, context, event):
        self.events.append(event)


class RecordingTransaction:
    """Runs the real SqlDataServiceExecutor.mutate boundary without a database."""

    def __init__(self, owner):
        self.owner = owner
        self.executor = object.__new__(SqlDataServiceExecutor)
        self.executor._sync_generated_schema = lambda context: None
        self.executor._mutate = self._mutate

    async def mutate(self, context, request):
        return await self.executor.mutate(context, request)

    async def _mutate(self, context, request):
        self.owner.mutations += 1
        command = request._data
        await context.send_audit_event(RawAuditEvent(
            MutationAuditKind.CREATED,
            command.entity,
            command.values.get("id"),
            (),
            tuple(request.trace_chain()),
            context.user_identifier(),
            "mutation-policy-test",
            context.current_mutation_governance(),
        ))
        now = datetime.now(timezone.utc)
        return MutationResult(
            affected_rows=1,
            generated_values={},
            persisted_record={
                key: value.val for key, value in command.values.items()
            },
            metadata=ExecutionMetadata(
                backend="test",
                operation=DataServiceOperation.Insert,
                started_at=now,
                ended_at=now,
                affected_rows=1,
            ),
        )

    async def commit(self, context):
        self.owner.commits += 1

    async def rollback(self, context):
        self.owner.rollbacks += 1


class RecordingProvider:
    def __init__(self):
        self.begins = 0
        self.mutations = 0
        self.commits = 0
        self.rollbacks = 0

    async def begin(self, context):
        self.begins += 1
        return RecordingTransaction(self)


def test_generated_default_and_exact_approval_warning_semantics():
    warnings = RecordingWarnings()
    context = UserContext.new().with_mutation_governance_sink(warnings)

    first = context.review_mutation_plan(_plan("one"))
    second = context.review_mutation_plan(_plan("two"))
    assert first.source == MutationPolicySource.GENERATED_DEFAULT
    assert first.warning_codes == (MISSING_POLICY,)
    assert second.approval_status == MutationPolicyApprovalStatus.NOT_APPLICABLE
    assert [event.first_occurrence for event in warnings.events] == [True, False]

    identity = MutationPolicyIdentity("orders", "3", "sha256:orders-v3")
    policy = TestPolicy(identity, lambda plan: MutationDecision.allowed())
    customer = (UserContext.new()
                .with_mutation_policy_registry(
                    DelegatingMutationPolicyRegistry(lambda _: policy))
                .with_mutation_governance_sink(warnings))
    missing = customer.review_mutation_plan(_plan("missing"))
    assert missing.warning_codes == (MISSING_APPROVAL,)

    wrong = MutationPolicyIdentity("orders", "3", "sha256:wrong")
    customer.with_mutation_policy_approval_provider(
        DelegatingMutationPolicyApprovalProvider(
            lambda _: MutationPolicyApproval(
                wrong, "security-owner", datetime.now(timezone.utc))))
    mismatched = customer.review_mutation_plan(_plan("mismatched"))
    assert mismatched.approval_status == MutationPolicyApprovalStatus.MISSING

    customer.with_mutation_policy_approval_provider(
        DelegatingMutationPolicyApprovalProvider(
            lambda candidate: MutationPolicyApproval(
                candidate, "security-owner", datetime.min)))
    default_time = customer.review_mutation_plan(_plan("default-time"))
    assert default_time.approval_status == MutationPolicyApprovalStatus.MISSING

    customer.with_mutation_policy_approval_provider(
        DelegatingMutationPolicyApprovalProvider(
            lambda candidate: MutationPolicyApproval(
                candidate, "security-owner", datetime.now(timezone.utc))))
    approved = customer.review_mutation_plan(_plan("approved"))
    assert approved.approval_status == MutationPolicyApprovalStatus.APPROVED
    assert approved.warning_codes == ()


@pytest.mark.asyncio
async def test_complete_graph_policy_audit_and_immutable_preflight():
    observed = {}
    identity = MutationPolicyIdentity("orders", "1", "sha256:orders")

    def review(plan):
        observed["count"] = len(plan.operations)
        observed["name"] = plan.operations[0].changed_values["name"].try_text()
        return MutationDecision.allowed()

    audit = RecordingAudit()
    provider = RecordingProvider()
    context = _context(provider, TestPolicy(identity, review), audit=audit, approval=True)
    order = _insert("Order", 42, "DRAFT")
    line = _insert("OrderLine", 99, "LINE")

    async def save_graph():
        context.preflight_mutation(order)
        context.preflight_mutation(line)
        order.values["name"] = Value.Text("APPROVED")
        # The policy still receives DRAFT, and an execution may only consume the
        # original reviewed operation rather than the changed command.
        transaction = context.require_resource("dataService")
        await transaction.mutate(
            context, MutationRequest(_insert("Order", 42, "DRAFT")))
        return await transaction.mutate(context, MutationRequest(line))

    await context.execute_graph_save(save_graph)
    assert observed == {"count": 2, "name": "DRAFT"}
    assert provider.mutations == 2
    assert provider.commits == 1
    assert provider.rollbacks == 0
    assert len(audit.events) == 2
    assert all(event.mutation_governance.policy == identity for event in audit.events)
    assert all(
        event.mutation_governance.approval_status
        == MutationPolicyApprovalStatus.APPROVED
        for event in audit.events
    )


@pytest.mark.asyncio
async def test_denial_and_missing_preflight_leave_zero_provider_mutations():
    identity = MutationPolicyIdentity("orders", "1", "sha256:deny")
    denied_provider = RecordingProvider()
    denied = _context(
        denied_provider,
        TestPolicy(
            identity,
            lambda plan: MutationDecision.denied(
                "ORDER_DENIED", "orders disabled", "Order.name")),
    )
    order = _insert("Order", 43, "DENIED")
    line = _insert("OrderLine", 100, "DENIED-LINE")

    async def denied_graph():
        denied.preflight_mutation(order)
        denied.preflight_mutation(line)
        return await denied.require_resource("dataService").mutate(
            denied, MutationRequest(order))

    with pytest.raises(MutationPolicyError, match="ORDER_DENIED"):
        await denied.execute_graph_save(denied_graph)
    assert denied_provider.begins == 1
    assert denied_provider.mutations == 0
    assert denied_provider.rollbacks == 1

    missing_provider = RecordingProvider()
    missing = _context(
        missing_provider,
        TestPolicy(identity, lambda plan: MutationDecision.allowed()),
    )
    with pytest.raises(MutationPolicyError, match="complete graph preflight"):
        await missing.execute_graph_save(
            lambda: missing.require_resource("dataService").mutate(
                missing, MutationRequest(_insert("Order", 44, "MISSING"))))
    assert missing_provider.mutations == 0
    assert missing_provider.rollbacks == 1


@pytest.mark.asyncio
async def test_generated_default_allows_legacy_graph_without_complete_preflight():
    provider = RecordingProvider()
    warnings = RecordingWarnings()
    context = (UserContext.new()
               .insert_resource("dataService", provider)
               .with_mutation_governance_sink(warnings))

    async def legacy_graph():
        transaction = context.require_resource("dataService")
        await transaction.mutate(
            context, MutationRequest(_insert("Order", 47, "FIRST")))
        await transaction.mutate(
            context, MutationRequest(_insert("OrderLine", 102, "SECOND")))

    await context.execute_graph_save(legacy_graph)
    assert provider.mutations == 2
    assert provider.commits == 1
    assert provider.rollbacks == 0
    assert [event.warning_code for event in warnings.events] == [MISSING_POLICY, MISSING_POLICY]


@pytest.mark.asyncio
async def test_unplanned_and_incomplete_operations_fail_closed():
    identity = MutationPolicyIdentity("orders", "1", "sha256:strict")
    unplanned_provider = RecordingProvider()
    unplanned = _context(
        unplanned_provider,
        TestPolicy(identity, lambda plan: MutationDecision.allowed()),
    )

    async def unplanned_graph():
        unplanned.preflight_mutation(_insert("Order", 45, "PLANNED"))
        return await unplanned.require_resource("dataService").mutate(
            unplanned, MutationRequest(_insert("Order", 45, "DIFFERENT")))

    with pytest.raises(MutationPolicyError, match="not present"):
        await unplanned.execute_graph_save(unplanned_graph)
    assert unplanned_provider.mutations == 0
    assert unplanned_provider.rollbacks == 1

    incomplete_provider = RecordingProvider()
    incomplete = _context(
        incomplete_provider,
        TestPolicy(identity, lambda plan: MutationDecision.allowed()),
    )
    first = _insert("Order", 46, "FIRST")
    second = _insert("OrderLine", 101, "SECOND")

    async def incomplete_graph():
        incomplete.preflight_mutation(first)
        incomplete.preflight_mutation(second)
        return await incomplete.require_resource("dataService").mutate(
            incomplete, MutationRequest(first))

    with pytest.raises(MutationPolicyError, match="were not executed"):
        await incomplete.execute_graph_save(incomplete_graph)
    assert incomplete_provider.mutations == 1
    assert incomplete_provider.commits == 0
    assert incomplete_provider.rollbacks == 1


@pytest.mark.asyncio
async def test_warning_sink_failure_is_fail_open():
    identity = MutationPolicyIdentity("orders", "1", "sha256:warning")
    provider = RecordingProvider()
    warnings = RecordingWarnings(RuntimeError("warning sink unavailable"))
    context = _context(
        provider,
        TestPolicy(identity, lambda plan: MutationDecision.allowed()),
        warning_sink=warnings,
    )
    order = _insert("Order", 47, "ALLOWED")

    async def graph():
        context.preflight_mutation(order)
        return await context.require_resource("dataService").mutate(
            context, MutationRequest(order))

    await context.execute_graph_save(graph)
    assert warnings.events[0].warning_code == MISSING_APPROVAL
    assert provider.mutations == 1
    assert provider.commits == 1


def _context(provider, policy, audit=None, approval=False, warning_sink=None):
    context = (UserContext.new()
               .insert_resource("dataService", provider)
               .with_trace_id("python-mutation-policy")
               .with_mutation_policy_registry(
                   DelegatingMutationPolicyRegistry(lambda _: policy)))
    if audit:
        context.with_app_audit_event_sink(audit)
    if approval:
        context.with_mutation_policy_approval_provider(
            DelegatingMutationPolicyApprovalProvider(
                lambda candidate: MutationPolicyApproval(
                    candidate, "security-owner", datetime.now(timezone.utc))))
    if warning_sink:
        context.with_mutation_governance_sink(warning_sink)
    return context


def _plan(execution_id):
    return MutationPlan(
        execution_id,
        "Order.saveGraph",
        "Order",
        "submit order",
        (
            MutationOperation(
                MutationOperationKind.UPDATE,
                "Order",
                Value.I64(42),
                7,
                {"name": Value.Text("Updated")},
            ),
        ),
    )


def _insert(entity, entity_id, name):
    command = InsertCommand.new(entity).value("id", entity_id).value("name", name)
    command.value("version", 1)
    command.trace_chain.append(TraceNode(entity, entity_id, f"create {entity}"))
    return command
