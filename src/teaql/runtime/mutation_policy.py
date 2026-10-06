"""Governed, whole-graph mutation policy contracts.

The policy receives a detached snapshot after Checker/Fix and before the first
provider mutation. Runtime-specific transaction setup may already have happened;
the portable guarantee is that no provider mutation has executed.
"""

from __future__ import annotations

import contextvars
import logging
import threading
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from types import MappingProxyType
from typing import Any, Callable, Mapping, Optional, Protocol, Sequence

from teaql.core.mutation import (
    DeleteCommand,
    InsertCommand,
    MutationRequest,
    RecoverCommand,
    UpdateCommand,
)
from teaql.core.value import Timestamp, Value


MISSING_POLICY = "MUTATION-POLICY-001"
MISSING_APPROVAL = "MUTATION-POLICY-002"


class MutationPolicyError(RuntimeError):
    pass


class MutationOperationKind(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    RECOVER = "recover"


@dataclass(frozen=True)
class MutationPolicyIdentity:
    policy_id: str
    version: str
    fingerprint: str

    def __post_init__(self) -> None:
        for name in ("policy_id", "version", "fingerprint"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError("mutation policy identity values must not be blank")
            object.__setattr__(self, name, value.strip())


@dataclass(frozen=True)
class MutationOperation:
    kind: MutationOperationKind
    entity: str
    entity_id: Optional[Value]
    original_version: Optional[int]
    changed_values: Mapping[str, Value]


@dataclass(frozen=True)
class MutationPlan:
    execution_id: str
    request_key: str
    root_entity_type: str
    audit_reason: Optional[str]
    operations: tuple[MutationOperation, ...]


class MutationVerdict(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass(frozen=True)
class MutationDecision:
    verdict: MutationVerdict
    code: Optional[str] = None
    message: Optional[str] = None
    field_paths: tuple[str, ...] = ()

    @classmethod
    def allowed(cls) -> "MutationDecision":
        return cls(MutationVerdict.ALLOW)

    @classmethod
    def denied(
        cls, code: str, message: str, *field_paths: str
    ) -> "MutationDecision":
        if not isinstance(code, str) or not code.strip():
            raise ValueError("a mutation policy denial code is required")
        return cls(MutationVerdict.DENY, code.strip(), message, tuple(field_paths))


class MutationPolicy(Protocol):
    identity: MutationPolicyIdentity

    def review(self, context: Any, plan: MutationPlan) -> MutationDecision:
        ...


class MutationPolicyRegistry(Protocol):
    def resolve(self, request_key: str) -> Optional[MutationPolicy]:
        ...


class DelegatingMutationPolicyRegistry:
    def __init__(self, resolve: Callable[[str], Optional[MutationPolicy]]):
        self._resolve = resolve

    def resolve(self, request_key: str) -> Optional[MutationPolicy]:
        return self._resolve(request_key)


@dataclass(frozen=True)
class MutationPolicyApproval:
    policy: MutationPolicyIdentity
    approved_by: str
    approved_at: datetime

    def is_valid_for(self, identity: MutationPolicyIdentity) -> bool:
        return (
            self.policy == identity
            and isinstance(self.approved_by, str)
            and bool(self.approved_by.strip())
            and isinstance(self.approved_at, datetime)
            and self.approved_at.replace(tzinfo=None) != datetime.min
        )


class MutationPolicyApprovalProvider(Protocol):
    def find_approval(
        self, identity: MutationPolicyIdentity
    ) -> Optional[MutationPolicyApproval]:
        ...


class DelegatingMutationPolicyApprovalProvider:
    def __init__(
        self,
        find: Callable[[MutationPolicyIdentity], Optional[MutationPolicyApproval]],
    ):
        self._find = find

    def find_approval(
        self, identity: MutationPolicyIdentity
    ) -> Optional[MutationPolicyApproval]:
        return self._find(identity)


class MutationPolicySource(str, Enum):
    GENERATED_DEFAULT = "generated_default"
    CUSTOMER = "customer"


class MutationPolicyApprovalStatus(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    MISSING = "missing"
    APPROVED = "approved"


@dataclass(frozen=True)
class MutationOperationSummary:
    kind: MutationOperationKind
    entity: str
    entity_id: Optional[Value]
    changed_fields: tuple[str, ...]


@dataclass(frozen=True)
class MutationGovernanceSnapshot:
    execution_id: str
    request_key: str
    source: MutationPolicySource
    policy: Optional[MutationPolicyIdentity]
    approval_status: MutationPolicyApprovalStatus
    warning_codes: tuple[str, ...]
    operations: tuple[MutationOperationSummary, ...]


@dataclass(frozen=True)
class MutationGovernanceEvent:
    snapshot: MutationGovernanceSnapshot
    warning_code: str
    first_occurrence: bool


class MutationGovernanceSink(Protocol):
    def on_warning(self, context: Any, warning: MutationGovernanceEvent) -> None:
        ...


class DelegatingMutationGovernanceSink:
    def __init__(self, warning: Callable[[Any, MutationGovernanceEvent], None]):
        self._warning = warning

    def on_warning(self, context: Any, warning: MutationGovernanceEvent) -> None:
        self._warning(context, warning)


class _TextMutationGovernanceSink:
    def on_warning(self, context: Any, warning: MutationGovernanceEvent) -> None:
        if not warning.first_occurrence:
            return
        logging.getLogger("teaql.mutation_policy").warning(
            "TeaQL mutation policy warning code=%s request_key=%s source=%s approval=%s",
            warning.warning_code,
            warning.snapshot.request_key,
            warning.snapshot.source.value,
            warning.snapshot.approval_status.value,
        )


class MutationPolicyRuntimeState:
    _sequence = 0
    _sequence_lock = threading.Lock()

    def __init__(self) -> None:
        self.registry: Optional[MutationPolicyRegistry] = None
        self.approval_provider: Optional[MutationPolicyApprovalProvider] = None
        self.warning_sink: MutationGovernanceSink = _TextMutationGovernanceSink()
        self._emitted_warnings: set[str] = set()
        self._warning_lock = threading.Lock()
        self._active = contextvars.ContextVar(
            f"teaql_mutation_policy_{id(self)}", default=None
        )
        self._graph_active = False
        self._graph_reviewed = False
        self._preflight: list[MutationOperation] = []
        self._root_entity: Optional[str] = None
        self._audit_reason: Optional[str] = None
        self._remaining: Counter[Any] = Counter()

    @property
    def current(self) -> Optional[MutationGovernanceSnapshot]:
        return self._active.get()

    def for_invocation(self) -> 'MutationPolicyRuntimeState':
        """Share configuration/warning dedup, never a graph's mutable plan."""
        state = MutationPolicyRuntimeState()
        state.registry = self.registry
        state.approval_provider = self.approval_provider
        state.warning_sink = self.warning_sink
        state._emitted_warnings = self._emitted_warnings
        state._warning_lock = self._warning_lock
        return state

    def begin_graph(self, audit_reason: str) -> None:
        from teaql.core.request_intent import MutationIntent
        intent = MutationIntent(audit_reason)
        self._graph_active = True
        self._graph_reviewed = False
        self._preflight.clear()
        self._root_entity = None
        self._audit_reason = intent.comment
        self._remaining.clear()
        self._active.set(None)

    def end_graph(self) -> None:
        self._graph_active = False
        self._graph_reviewed = False
        self._preflight.clear()
        self._root_entity = None
        self._audit_reason = None
        self._remaining.clear()
        self._active.set(None)

    def record_preflight(self, command: Any) -> None:
        if not self._graph_active:
            return
        if self._graph_reviewed:
            raise MutationPolicyError(
                "mutation preflight cannot add operations after policy review"
            )
        operations = _operations_from_data(command)
        if not operations:
            raise MutationPolicyError("mutation preflight must contain an operation")
        self._root_entity = self._root_entity or operations[0].entity
        self._preflight.extend(operations)

    def enter_mutation(self, context: Any, request: MutationRequest):
        request.validate()
        operations = _operations_from_data(request._data)
        if not operations:
            raise MutationPolicyError("mutation request must contain an operation")
        # Legacy/manual graph transactions cannot describe the complete graph
        # before their first provider call. Keep those writes governed by the
        # generated-default policy one operation at a time. Installing a
        # customer policy still requires a complete preflight and therefore
        # remains fail-closed.
        if self._graph_active and self.registry is None and not self._preflight:
            plan = self._build_plan(
                context, operations[0].entity, self._audit_reason, tuple(operations)
            )
            token = self._active.set(self.review(context, plan))
            return _ResetScope(self._active, token)
        if self._graph_active:
            if not self._graph_reviewed:
                if self.registry is not None and not self._preflight:
                    raise MutationPolicyError(
                        "customer mutation policy requires complete graph preflight "
                        "before provider mutation"
                    )
                planned = tuple(self._preflight or operations)
                root = self._root_entity or planned[0].entity
                reason = self._audit_reason
                snapshot = self.review(context, self._build_plan(context, root, reason, planned))
                self._active.set(snapshot)
                self._remaining = Counter(_operation_signature(item) for item in planned)
                self._graph_reviewed = True
            self._consume_planned(operations)
            return _NoopScope()

        plan = self._build_plan(
            context, operations[0].entity, _request_comment(request), tuple(operations)
        )
        token = self._active.set(self.review(context, plan))
        return _ResetScope(self._active, token)

    def ensure_graph_complete(self) -> None:
        if self._graph_reviewed and self._remaining:
            raise MutationPolicyError(
                "reviewed mutation plan contains operations that were not executed"
            )

    def review(self, context: Any, plan: MutationPlan) -> MutationGovernanceSnapshot:
        _validate_plan(plan)
        policy = self.registry.resolve(plan.request_key) if self.registry else None
        if policy is None:
            source = MutationPolicySource.GENERATED_DEFAULT
            identity = None
            approval = MutationPolicyApprovalStatus.NOT_APPLICABLE
            warnings = (MISSING_POLICY,)
        else:
            identity = policy.identity
            if not isinstance(identity, MutationPolicyIdentity):
                raise MutationPolicyError("customer mutation policy identity is invalid")
            decision = policy.review(context, _clone_plan(plan))
            if not isinstance(decision, MutationDecision):
                raise MutationPolicyError("customer mutation policy returned an invalid decision")
            if decision.verdict == MutationVerdict.DENY:
                raise MutationPolicyError(
                    f"[MUTATION POLICY DENIED] "
                    f"{decision.code or 'MUTATION-POLICY-DENIED'}: "
                    f"{decision.message or 'mutation rejected'}"
                )
            if decision.verdict != MutationVerdict.ALLOW:
                raise MutationPolicyError("customer mutation policy returned an invalid verdict")
            source = MutationPolicySource.CUSTOMER
            found = (
                self.approval_provider.find_approval(identity)
                if self.approval_provider
                else None
            )
            approval = (
                MutationPolicyApprovalStatus.APPROVED
                if found is not None and found.is_valid_for(identity)
                else MutationPolicyApprovalStatus.MISSING
            )
            warnings = () if approval == MutationPolicyApprovalStatus.APPROVED else (MISSING_APPROVAL,)

        snapshot = MutationGovernanceSnapshot(
            execution_id=plan.execution_id,
            request_key=plan.request_key,
            source=source,
            policy=identity,
            approval_status=approval,
            warning_codes=warnings,
            operations=tuple(
                MutationOperationSummary(
                    item.kind,
                    item.entity,
                    _clone_value(item.entity_id) if item.entity_id else None,
                    tuple(sorted(item.changed_values)),
                )
                for item in plan.operations
            ),
        )
        for warning in warnings:
            self._emit_warning(context, snapshot, warning)
        return snapshot

    def _consume_planned(self, operations: Sequence[MutationOperation]) -> None:
        for operation in operations:
            signature = _operation_signature(operation)
            if self._remaining[signature] <= 0:
                raise MutationPolicyError(
                    "provider mutation is not present in the reviewed graph plan"
                )
            self._remaining[signature] -= 1
            if self._remaining[signature] == 0:
                del self._remaining[signature]

    def _build_plan(
        self,
        context: Any,
        root: str,
        reason: Optional[str],
        operations: tuple[MutationOperation, ...],
    ) -> MutationPlan:
        with self._sequence_lock:
            type(self)._sequence += 1
            sequence = type(self)._sequence
        trace_id = getattr(context, "trace_id", lambda: "")()
        return MutationPlan(
            execution_id=f"{trace_id or 'teaql'}-mutation-{sequence}",
            request_key=f"{root}.saveGraph",
            root_entity_type=root,
            audit_reason=reason,
            operations=tuple(_clone_operation(item) for item in operations),
        )

    def _emit_warning(
        self,
        context: Any,
        snapshot: MutationGovernanceSnapshot,
        warning_code: str,
    ) -> None:
        identity = (
            "none"
            if snapshot.policy is None
            else f"{snapshot.policy.policy_id}:{snapshot.policy.version}:"
                 f"{snapshot.policy.fingerprint}"
        )
        key = f"{snapshot.request_key}|{identity}|{warning_code}"
        with self._warning_lock:
            first = key not in self._emitted_warnings
            self._emitted_warnings.add(key)
        try:
            self.warning_sink.on_warning(
                context,
                MutationGovernanceEvent(snapshot, warning_code, first),
            )
        except BaseException:
            # Warning delivery must not change business persistence semantics.
            pass


class _NoopScope:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class _ResetScope:
    def __init__(self, variable: contextvars.ContextVar, token: contextvars.Token):
        self._variable = variable
        self._token = token

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._variable.reset(self._token)
        return False


def _operations_from_data(data: Any) -> list[MutationOperation]:
    if isinstance(data, MutationRequest):
        return _operations_from_data(data._data)
    if isinstance(data, list):
        operations: list[MutationOperation] = []
        for item in data:
            operations.extend(_operations_from_data(item))
        return operations
    if isinstance(data, InsertCommand):
        return [MutationOperation(
            MutationOperationKind.CREATE,
            data.entity,
            _clone_value(data.values.get("id")),
            None,
            _readonly_values(data.values),
        )]
    if isinstance(data, UpdateCommand):
        return [MutationOperation(
            MutationOperationKind.UPDATE,
            data.entity,
            _clone_value(data.id),
            data.expected_version_val,
            _readonly_values(data.values),
        )]
    if isinstance(data, DeleteCommand):
        return [MutationOperation(
            MutationOperationKind.DELETE,
            data.entity,
            _clone_value(data.id),
            data.expected_version_val,
            MappingProxyType({}),
        )]
    if isinstance(data, RecoverCommand):
        return [MutationOperation(
            MutationOperationKind.RECOVER,
            data.entity,
            _clone_value(data.id),
            data.expected_version_val,
            MappingProxyType({}),
        )]
    raise MutationPolicyError(f"unsupported mutation command {type(data).__name__}")


def _comment_from_data(data: Any) -> Optional[str]:
    if isinstance(data, MutationRequest):
        return _request_comment(data)
    if isinstance(data, list):
        for item in data:
            comment = _comment_from_data(item)
            if comment:
                return comment
        return None
    traces = getattr(data, "trace_chain", ())
    return traces[-1].comment if traces else None


def _request_comment(request: MutationRequest) -> Optional[str]:
    comment = getattr(request, "comment", None)
    return comment() if callable(comment) else comment


def _readonly_values(values: Mapping[str, Value]) -> Mapping[str, Value]:
    return MappingProxyType({key: _clone_value(value) for key, value in values.items()})


def _clone_value(value: Optional[Value]) -> Optional[Value]:
    if value is None:
        return None
    raw = value.val
    if hasattr(raw, "id"):
        raw = getattr(raw, "id")
    else:
        try:
            raw = deepcopy(raw)
        except BaseException:
            raw = repr(raw)
    return Value(raw, getattr(value, "_type_hint", None))


def _clone_operation(operation: MutationOperation) -> MutationOperation:
    return MutationOperation(
        operation.kind,
        operation.entity,
        _clone_value(operation.entity_id),
        operation.original_version,
        _readonly_values(operation.changed_values),
    )


def _clone_plan(plan: MutationPlan) -> MutationPlan:
    return MutationPlan(
        plan.execution_id,
        plan.request_key,
        plan.root_entity_type,
        plan.audit_reason,
        tuple(_clone_operation(item) for item in plan.operations),
    )


def _validate_plan(plan: MutationPlan) -> None:
    if not isinstance(plan.execution_id, str) or not plan.execution_id.strip():
        raise MutationPolicyError("mutation plan execution id is required")
    if not isinstance(plan.request_key, str) or not plan.request_key.strip():
        raise MutationPolicyError("mutation plan request key is required")
    if not isinstance(plan.root_entity_type, str) or not plan.root_entity_type.strip():
        raise MutationPolicyError("mutation plan root entity type is required")
    if not plan.operations:
        raise MutationPolicyError("mutation plan must contain an operation")
    if any(not item.entity for item in plan.operations):
        raise MutationPolicyError("mutation operation entity type is required")


def _operation_signature(operation: MutationOperation):
    return (
        operation.kind.value,
        operation.entity,
        _freeze_value(operation.entity_id),
        operation.original_version,
        tuple(
            (key, _freeze_value(value))
            for key, value in sorted(operation.changed_values.items())
        ),
    )


def _freeze_value(value: Optional[Value]):
    if value is None:
        return None
    raw = value.val
    hint = getattr(getattr(value, "_type_hint", None), "name", None)
    return (hint, _freeze_raw(raw))


def _freeze_raw(value: Any):
    if isinstance(value, Value):
        return _freeze_value(value)
    if isinstance(value, Mapping):
        return tuple((str(key), _freeze_raw(item)) for key, item in sorted(value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_raw(item) for item in value)
    if isinstance(value, Timestamp):
        return ("timestamp", value.millis)
    if isinstance(value, (date, datetime)):
        return (type(value).__name__, value.isoformat())
    if isinstance(value, Decimal):
        return ("decimal", str(value))
    if hasattr(value, "id"):
        return (type(value).__name__, _freeze_raw(getattr(value, "id")))
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    return (type(value).__name__, repr(value))
