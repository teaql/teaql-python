"""One explicit graph-save session. Context supplies configuration, not lineage."""

from copy import copy, deepcopy
from inspect import isawaitable

from teaql.core.mutation import MutationRequest
from teaql.core.request_intent import MutationIntent
from teaql.core.trace_scope import TraceScope


class GraphCommittedError(RuntimeError):
    """Database commit succeeded; delivery/cleanup failed. Never retry the write."""

    committed = True

    def __init__(self, failures):
        self.failures = tuple(failures)
        super().__init__('graph committed; one or more completion actions failed')


class GraphMutationSession:
    def __init__(self, context, transaction, intent: MutationIntent):
        from .log_privacy import _MutationIntentPrivacy
        self._intent_privacy = _MutationIntentPrivacy()
        self.intent = intent
        self.transaction = transaction
        self._owner = object()
        self._active = True
        self._committed = False
        self._commit_actions = []
        self._rollback_actions = []
        self._audits = []
        # Preserve customer UserContext overrides and configured services. Only
        # mutable invocation state is detached; diagnostic destinations are shared.
        view = copy(context)
        context._resources.setdefault('sql_logs', [])
        view._resources = dict(context._resources)
        view._resources['dataService'] = transaction
        view._resources['fix_time'] = context.business_time()
        view._mutation_policy = context._mutation_policy.for_invocation()
        view._mutation_policy.begin_graph(intent.comment)
        view._checked_mutations = set()
        view._fix_evidence_current = []
        view._fix_evidence_last = []
        view._graph_session = self
        self.context = view

    def _require_active(self):
        if not self._active or self._committed:
            raise RuntimeError('graph mutation session is no longer writable')

    def scope(self, key, parent=None, local_reason=None):
        self._require_active()
        if parent is None:
            return TraceScope.root(self._owner, key, self.intent.comment)
        if not isinstance(parent, TraceScope) or parent._owner is not self._owner:
            raise ValueError('graph trace scope belongs to another invocation')
        return parent.child(key, local_reason)

    def request(self, command, scope, ledger=None, key=None):
        self._require_active()
        if not isinstance(scope, TraceScope) or scope._owner is not self._owner:
            raise ValueError('graph trace scope belongs to another invocation')
        specific = ledger.trace_chain(key) if ledger is not None and key is not None else ()
        return MutationRequest(command, comment=self.intent.comment).with_mutation_lineage(
            specific or scope.recover())

    def after_commit(self, action):
        self._require_active()
        self._commit_actions.append(action)

    def after_rollback(self, action):
        self._require_active()
        self._rollback_actions.append(action)

    def queue_audit(self, event, safe_event):
        self._require_active()
        self._audits.append((deepcopy(event), deepcopy(safe_event)))

    async def committed(self):
        self._committed = True
        failures = []
        # A failed sink must not prevent subsequent events or ledger cleanup.
        for event, safe_event in self._audits:
            try:
                await self.context._deliver_audit_event(event, safe_event)
            except BaseException as error:
                failures.append(error)
        for action in self._commit_actions:
            try:
                result = action()
                if isawaitable(result):
                    await result
            except BaseException as error:
                failures.append(error)
        if failures:
            raise GraphCommittedError(failures)

    async def rolled_back(self):
        # Rollback evidence must never escape as a committed audit event.
        self._audits.clear()
        failures = []
        for action in reversed(self._rollback_actions):
            try:
                result = action()
                if isawaitable(result):
                    await result
            except BaseException as error:
                failures.append(error)
        return tuple(failures)

    def close(self):
        from .log_privacy import _MutationIntentPrivacy
        self._intent_privacy = _MutationIntentPrivacy()
        self._active = False
        self.context._mutation_policy.end_graph()
        self.context.finish_fix_evidence()
        self.context._resources.pop('fix_time', None)
        self._audits.clear()
        self._commit_actions.clear()
        self._rollback_actions.clear()
