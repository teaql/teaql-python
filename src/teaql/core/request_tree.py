"""Immutable request ownership; never part of query JSON or UserContext state."""
from dataclasses import dataclass, field
import re
import weakref
from typing import Any, Optional


@dataclass(frozen=True, slots=True)
class QueryOperation:
    kind: str
    method: Optional[str] = None
    alias: Optional[str] = field(default=None, repr=False)
    relation: Optional[str] = None

    def __post_init__(self):
        if (self.kind not in ('named-count', 'facet', 'relation-count', 'relation-select',
                              'aggregate', 'pagination')
                or self.method is not None and (
                    not isinstance(self.method, str)
                    or re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', self.method) is None)
                or self.alias is not None and not isinstance(self.alias, str)
                or self.relation is not None and not isinstance(self.relation, str)):
            raise ValueError('QUERY_OPERATION_INVALID: invalid generated operation descriptor')

    def comment(self) -> str:
        def literal(text):
            return "'" + (text.replace('\\', '\\\\').replace("'", "\\'")
                         .replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                         .replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')) + "'"
        if self.method is None:
            return ('framework: ' + self.kind + (' ' + self.relation if self.relation else '')
                    + (' ' + literal(self.alias) if self.alias is not None else ''))
        argument = literal(self.alias) if self.alias is not None else (
            '...' if self.kind == 'relation-select' else '')
        return self.method + '(' + argument + ')'


@dataclass(frozen=True, slots=True)
class _RequestOwner:
    parent: Any = field(repr=False)
    name: str
    comment: str = field(repr=False)
    intent: Any = field(repr=False)
    operation: Optional[QueryOperation] = None
    source: tuple = field(default=(), repr=False)
    invocation: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self.parent is not None:
            object.__setattr__(self, 'invocation', self.parent._invocation_identity)
        elif self.invocation is None:
            object.__setattr__(self, 'invocation', object())


# SelectQuery is mutable and unhashable, so WeakKeyDictionary is unsuitable.
# Identity is checked on both lookup and finalization to avoid id reuse. Values
# hold immutable ownership, not the owning query/request itself.
_owners = {}


def _owner_for(query):
    item = _owners.get(id(query))
    return item[1] if item is not None and item[0]() is query else None


def _retain_owner(query, owner):
    key = id(query)
    def remove(reference):
        current = _owners.get(key)
        if current is not None and current[0] is reference:
            _owners.pop(key, None)
    _owners[key] = (weakref.ref(query, remove), owner)


def _copy_owner(source, target):
    owner = _owner_for(source)
    if owner is not None:
        _retain_owner(target, owner)
