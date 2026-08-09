from typing import Any, Dict

class GraphNode:
    def __init__(self, entity: str):
        self.entity = entity
        self.values: Dict[str, Any] = {}
        
    def set(self, key: str, value: Any) -> 'GraphNode':
        self.values[key] = value
        return self
