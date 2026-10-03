"""Typed physical SQL paths, distinct from graph mutation audit lineage."""
from copy import deepcopy
from dataclasses import replace
from typing import Iterable, List, Optional

from .mutation import TraceNode


def _kind(node: TraceNode) -> str:
    return str(node.kind).replace('_', '').lower()


def trace_name(node: TraceNode) -> str:
    return node.name or node.entity_type


def canonical_sql_trace_path(source: Iterable[TraceNode], backend: str,
                             operation: str) -> List[TraceNode]:
    """Rust baseline algorithm; owns output and is idempotent for canonical input."""
    nodes = list(source)
    intent_kinds = {'comment', 'purpose', 'auditreason'}
    kinds = {_kind(node) for node in nodes}
    if {'operation', 'provider', 'sql'} <= kinds:
        return deepcopy([node for node in nodes if _kind(node) not in intent_kinds])
    root = next((trace_name(node) for node in nodes if trace_name(node).strip()), 'unknown')
    query = operation.lower() == 'select'
    entity = root if query else next((trace_name(node) for node in reversed(nodes)
                                     if _kind(node) == 'entity' and trace_name(node).strip()), root)
    return [TraceNode(kind='operation', name=root, comment='query' if query else 'mutation'),
            TraceNode(kind='request' if query else 'entity', name=entity),
            *deepcopy([node for node in nodes if _kind(node) == 'relation']),
            TraceNode(kind='provider', name=backend if backend and backend.strip() else 'unknown'),
            TraceNode(kind='sql', name=operation.lower())]


def trace_intent(source: Iterable[TraceNode]) -> dict[str, Optional[str]]:
    result = {'comment': None, 'purpose': None, 'auditReason': None}
    names = {'comment': 'comment', 'purpose': 'purpose', 'auditreason': 'auditReason'}
    for node in source:
        name = names.get(_kind(node))
        if name is not None:
            result[name] = node.comment
    return result


def physical_readback_path(write_path: Iterable[TraceNode]) -> List[TraceNode]:
    """A real SELECT keeps its mutation origin but uses a query request frame."""
    nodes = list(write_path)
    root = next((trace_name(node) for node in nodes if _kind(node) == 'operation'), 'unknown')
    result = []
    for node in nodes:
        kind = _kind(node)
        if kind == 'operation':
            result.append(replace(node, comment='query'))
        elif kind == 'entity':
            result.append(TraceNode(kind='request', name=root))
        elif kind == 'sql':
            result.append(replace(node, name='select', comment=''))
        else:
            result.append(deepcopy(node))
    return result
