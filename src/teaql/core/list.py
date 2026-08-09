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

