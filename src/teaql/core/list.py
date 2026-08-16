from typing import Any, Callable, Dict, Generic, Iterable, List, Optional, TypeVar
from dataclasses import dataclass

T = TypeVar("T")

@dataclass(frozen=True)
class TeaQLPage(Generic[T]):
    data: 'SmartList[T]'
    total_count: int
    offset: int
    limit: int

class SmartList(List[T], Generic[T]):
    def __init__(self, data: Iterable[T] = (), facets: Optional[Dict[str, Any]] = None,
                 total_count: Optional[int] = None):
        super().__init__(data)
        self.facets = facets or {}
        self.total_count = total_count if total_count is not None else len(self)

    @property
    def data(self) -> 'SmartList[T]':
        return self

    def facet(self, name: str) -> Any:
        return self.facets.get(name)

    def map(self, f: Callable[[T], Any]) -> 'SmartList[Any]':
        return SmartList((f(x) for x in self), self.facets, self.total_count)

    def filter(self, f) -> 'SmartList':
        return SmartList((x for x in self if f(x)), self.facets, self.total_count)

    def flat_map(self, f) -> 'SmartList':
        result = []
        for x in self:
            result.extend(f(x))
        return SmartList(result, self.facets, self.total_count)

    def first(self) -> Any:
        return self[0] if self else None

    def last(self) -> Any:
        return self[-1] if self else None

    def is_empty(self) -> bool:
        return len(self) == 0

    def into_vec(self) -> List[Any]:
        return list(self)

    def get(self, index: int) -> Any:
        if 0 <= index < len(self):
            return self[index]
        return None

    def retain(self, f):
        self[:] = [x for x in self if f(x)]

def to_list(lst: SmartList) -> List[Any]:
    return list(lst)

def to_set(lst: SmartList) -> set:
    return set(lst.data)

def identity_map(lst: SmartList) -> Dict[Any, Any]:
    return {x: x for x in lst.data}

def group_by(lst: SmartList, key_func) -> Dict[Any, List[Any]]:
    result = {}
    for item in lst.data:
        key = key_func(item)
        if key not in result:
            result[key] = []
        result[key].append(item)
    return result

def into_records(lst: SmartList) -> List[Dict[str, Any]]:
    # Assuming the elements are entities with a .values dict or similar, or they are just dicts
    return [x.values if hasattr(x, 'values') else dict(x) for x in lst.data]

def ids(lst: SmartList) -> List[Any]:
    # Assuming elements have a .get('id') or similar
    return [x.get('id') if isinstance(x, dict) else getattr(x, 'id', None) for x in lst.data]

def map_by_id(lst: SmartList) -> Dict[Any, Any]:
    return { (x.get('id') if isinstance(x, dict) else getattr(x, 'id', None)): x for x in lst.data }

def versions(lst: SmartList) -> List[Any]:
    return [x.get('version') if isinstance(x, dict) else getattr(x, 'version', None) for x in lst.data]
