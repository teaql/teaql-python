"""Lifecycle of an explicit UserContext transaction and its graph saves."""

import asyncio

from .graph_session import GraphCommittedError


class TransactionOutcomeUnknown(RuntimeError):
    """The database did not confirm the outcome. Reload before resuming work."""

    def __init__(self):
        super().__init__("transaction outcome unknown; reload the affected records")


class _ContextTransaction:
    def __init__(self):
        self.owner = asyncio.current_task()
        self.active = True
        self.failure = None
        self.graphs = []
        self.entities = {}

    def require_access(self):
        if not self.active:
            raise RuntimeError("transaction context is closed")
        if asyncio.current_task() is not self.owner:
            raise RuntimeError("transaction context belongs to another task")

    def fail(self, error):
        if self.failure is None:
            self.failure = error

    def require_writable(self):
        self.require_access()
        if self.failure is not None:
            raise RuntimeError("transaction is marked for rollback") from self.failure

    async def complete_graphs(self, committed):
        failures = []
        for graph in self.graphs if committed else reversed(self.graphs):
            try:
                if committed:
                    await graph.committed()
                else:
                    await graph.rolled_back()
            except GraphCommittedError as error:
                failures.extend(error.failures)
            except BaseException as error:
                failures.append(error)
        return failures

    def fence_graphs(self):
        for entity in self.entities.values():
            self.fence_entity(entity)
        for graph in self.graphs:
            for entity, _, _ in graph._prepared_mutations.values():
                self.fence_entity(entity)

    @staticmethod
    def fence_entity(entity):
        ledger = getattr(entity, "_entity_root", None)
        if ledger is not None:
            ledger.fence_unknown_outcome()
            entity._teaql_transaction_outcome_unknown = True

    def close(self):
        self.active = False
        for graph in self.graphs:
            graph.close()
        self.graphs.clear()
        self.entities.clear()
