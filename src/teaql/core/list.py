from typing import Any, List, Dict, Iterator

class SmartList:
    def __init__(self, data: List[Any], facets: Dict[str, Any] = None, total_count: int = None):
        self.data = data
        self.facets = facets or {}
        self.total_count = total_count if total_count is not None else len(data)

    def facet(self, name: str) -> Any:
        return self.facets.get(name)

    def __iter__(self) -> Iterator[Any]:
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)

    def map(self, f) -> 'SmartList':
        return SmartList([f(x) for x in self.data], self.facets, self.total_count)

    def filter(self, f) -> 'SmartList':
        return SmartList([x for x in self.data if f(x)], self.facets, self.total_count)

    def flat_map(self, f) -> 'SmartList':
        result = []
        for x in self.data:
            result.extend(f(x))
        return SmartList(result, self.facets, self.total_count)

    def first(self) -> Any:
        return self.data[0] if self.data else None

    def last(self) -> Any:
        return self.data[-1] if self.data else None

    def is_empty(self) -> bool:
        return len(self.data) == 0

    def into_vec(self) -> List[Any]:
        return self.data

    def get(self, index: int) -> Any:
        if 0 <= index < len(self.data):
            return self.data[index]
        return None

    def retain(self, f):
        self.data = [x for x in self.data if f(x)]

def to_list(lst: SmartList) -> List[Any]:
    return lst.data

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
