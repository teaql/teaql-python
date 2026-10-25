from typing import Any, Callable, Dict, Generic, Iterable, List, Optional, TypeVar
from dataclasses import dataclass
from copy import deepcopy

T = TypeVar("T")
U = TypeVar("U")
K = TypeVar("K")

@dataclass(frozen=True)
class TeaQLPage(Generic[T]):
    data: 'SmartList[T]'
    total_count: int
    offset: int
    limit: int

class SmartList(List[T], Generic[T]):
    """Typed rows plus a source-query metadata snapshot.

    Construction copies metadata recursively; entity rows retain normal list semantics.
    In-place edits retain the source snapshot. Derived filter/flat_map clear it.
    """
    def __init__(self, data: Iterable[T] = (),
                 facets: Optional[Dict[str, 'SmartList[Dict[str, Any]]']] = None,
                 total_count: Optional[int] = None, aggregations: Optional[Dict[str, Any]] = None,
                 *, summary: Optional[Dict[str, Any]] = None):
        super().__init__(data)
        if total_count is not None and (isinstance(total_count, bool)
                or not isinstance(total_count, int) or total_count < 0):
            raise ValueError("total_count must be an exact non-negative integer")
        self.facets: Dict[str, SmartList[Dict[str, Any]]] = {
            name: deepcopy(facet) if isinstance(facet, SmartList) else SmartList(facet)
            for name, facet in (facets or {}).items()
        }
        self.total_count = total_count
        self.aggregations = deepcopy(aggregations or {})
        self.summary = deepcopy(summary or {})
        self._is_loaded = True

    @classmethod
    def empty(cls) -> 'SmartList[T]':
        result = cls()
        result._is_loaded = False
        return result

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    def total_count_or_len(self) -> int:
        return self.total_count if self.total_count is not None else len(self)

    @property
    def data(self) -> 'SmartList[T]':
        return self

    def facet(self, name: str) -> Optional['SmartList[Dict[str, Any]]']:
        return self.facets.get(name)

    def remove_facet(self, name: str) -> Optional['SmartList[Dict[str, Any]]']:
        return self.facets.pop(name, None)

    def take_facets(self) -> Dict[str, 'SmartList[Dict[str, Any]]']:
        facets, self.facets = self.facets, {}
        return facets

    def map(self, f: Callable[[T], U]) -> 'SmartList[U]':
        result = SmartList((f(x) for x in self), self.facets, self.total_count,
                           self.aggregations, summary=self.summary)
        result._is_loaded = self._is_loaded
        return result

    def filter(self, f: Callable[[T], bool]) -> 'SmartList[T]':
        result = SmartList(x for x in self if f(x))
        result._is_loaded = self._is_loaded
        return result

    def flat_map(self, f: Callable[[T], Iterable[U]]) -> 'SmartList[U]':
        result = SmartList(value for x in self for value in f(x))
        result._is_loaded = self._is_loaded
        return result

    def merge_by(self, incoming: Iterable[T], key: Callable[[T], K]) -> None:
        positions = {key(item): index for index, item in enumerate(self)}
        for item in incoming:
            item_key = key(item)
            if item_key in positions:
                self[positions[item_key]] = item
            else:
                positions[item_key] = len(self)
                self.append(item)

    def identity_map(self, key: Callable[[T], K]) -> Dict[K, T]:
        return {key(item): item for item in self}

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

def identity_map(lst: SmartList[T], key_func: Callable[[T], K] = lambda value: value) -> Dict[K, T]:
    return lst.identity_map(key_func)

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
    return {identifier: item for identifier, item in zip(ids(lst), lst) if identifier is not None}

def versions(lst: SmartList) -> List[Any]:
    return [x.get('version') if isinstance(x, dict) else getattr(x, 'version', None) for x in lst.data]
