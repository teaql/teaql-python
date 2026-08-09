from typing import Any, List, Dict, Iterator

class SmartList:
    def __init__(self, data: List[Any], facets: Dict[str, Any] = None):
        self.data = data
        self.facets = facets or {}

    def facet(self, name: str) -> Any:
        return self.facets.get(name)

    def __iter__(self) -> Iterator[Any]:
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)

