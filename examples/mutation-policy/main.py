"""Focused Mutation Policy example with an atomic in-memory transaction."""

import asyncio
from datetime import datetime, timezone

from teaql.core.mutation import InsertCommand, MutationRequest, TraceNode
from teaql.data_service import DataServiceOperation, ExecutionMetadata, MutationResult
from teaql.runtime import (
    DelegatingMutationPolicyApprovalProvider,
    DelegatingMutationPolicyRegistry,
    MutationDecision,
    MutationPolicyApproval,
    MutationPolicyApprovalStatus,
    MutationPolicyError,
    MutationPolicyIdentity,
    UserContext,
)
from teaql.runtime.audit import MutationAuditKind, RawAuditEvent


class OrderPolicy:
    identity = MutationPolicyIdentity(
        "order-submission", "1", "sha256:order-submission-v1"
    )

    def review(self, context, plan):
        if any(
            operation.changed_values.get("name").try_text() == "DENIED"
            for operation in plan.operations
            if operation.changed_values.get("name") is not None
        ):
            return MutationDecision.denied(
                "ORDER_DENIED", "the order policy rejected this graph", "Order.name"
            )
        return MutationDecision.allowed()


class AuditRecorder:
    def __init__(self):
        self.events = []

    async def on_safe_event(self, context, event):
        self.events.append(event)


class MemoryTransaction:
    def __init__(self, provider):
        self.provider = provider
        self.pending = []

    async def mutate(self, context, request):
        with context.mutation_policy_execution(request):
            command = request._data
            self.pending.append(command.entity)
            await context.send_audit_event(
                RawAuditEvent(
                    MutationAuditKind.CREATED,
                    command.entity,
                    command.values.get("id"),
                    (),
                    tuple(request.trace_chain()),
                    context.user_identifier(),
                    "mutation-policy-example",
                    context.current_mutation_governance(),
                )
            )
            now = datetime.now(timezone.utc)
            return MutationResult(
                affected_rows=1,
                generated_values={},
                persisted_record={
                    key: value.val for key, value in command.values.items()
                },
                metadata=ExecutionMetadata(
                    backend="memory-example",
                    operation=DataServiceOperation.Insert,
                    started_at=now,
                    ended_at=now,
                    affected_rows=1,
                ),
            )

    async def commit(self, context):
        self.provider.persisted.extend(self.pending)

    async def rollback(self, context):
        self.pending.clear()


class MemoryProvider:
    def __init__(self):
        self.persisted = []

    async def begin(self, context):
        return MemoryTransaction(self)


def insert(entity, entity_id, name):
    command = (
        InsertCommand.new(entity)
        .value("id", entity_id)
        .value("version", 1)
        .value("name", name)
    )
    command.trace_chain.append(TraceNode(entity, entity_id, f"create {entity}"))
    return command


def context_for(provider, audit):
    policy = OrderPolicy()
    return (
        UserContext.new()
        .insert_resource("dataService", provider)
        .with_trace_id("python-mutation-policy-example")
        .with_app_audit_event_sink(audit)
        .with_mutation_policy_registry(
            DelegatingMutationPolicyRegistry(lambda request_key: policy)
        )
        .with_mutation_policy_approval_provider(
            DelegatingMutationPolicyApprovalProvider(
                lambda identity: MutationPolicyApproval(
                    identity, "security-owner", datetime.now(timezone.utc)
                )
            )
        )
    )


async def save(context, *commands):
    async def graph():
        transaction = context.require_resource("dataService")
        for command in commands:
            context.preflight_mutation(command)
        for command in commands:
            await transaction.mutate(context, MutationRequest(command))

    await context.execute_graph_save(graph)


async def main():
    provider = MemoryProvider()
    audit = AuditRecorder()
    allowed = context_for(provider, audit)
    await save(
        allowed,
        insert("Order", 42, "SUBMITTED"),
        insert("OrderLine", 99, "LINE-1"),
    )

    denied_provider = MemoryProvider()
    denied = context_for(denied_provider, AuditRecorder())
    try:
        await save(denied, insert("Order", 43, "DENIED"))
    except MutationPolicyError as error:
        assert "ORDER_DENIED" in str(error)
    else:
        raise AssertionError("denied graph unexpectedly persisted")

    assert provider.persisted == ["Order", "OrderLine"]
    assert denied_provider.persisted == []
    assert len(audit.events) == 2
    assert all(
        event.mutation_governance.approval_status
        == MutationPolicyApprovalStatus.APPROVED
        for event in audit.events
    )
    print(
        "PYTHON_MUTATION_POLICY_PASS "
        "allowed_operations=2 denied_provider_mutations=0 audit_events=2"
    )


if __name__ == "__main__":
    asyncio.run(main())
