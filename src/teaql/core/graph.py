from typing import Any, Dict, List, Optional
from enum import Enum

class EntityGraphOperation(Enum):
    SAVE = 1
    DELETE = 2

class GraphNode:
    def __init__(self, entity: str):
        self.entity = entity
        self.fields: Dict[str, Any] = {}
        self.is_deleted: bool = False
        self.comment_text: Optional[str] = None
        self.children: Dict[str, List['GraphNode']] = {}

    def child(self, rel: str) -> 'GraphNode':
        if rel not in self.children:
            self.children[rel] = []
        node = GraphNode(rel)
        self.children[rel].append(node)
        return node

    def relation(self, rel: str) -> 'GraphNode':
        return self.child(rel)

    def relations(self) -> Dict[str, List['GraphNode']]:
        return self.children

    def remove(self, rel: str):
        if rel in self.children:
            del self.children[rel]

    def set(self, field: str, val: Any) -> 'GraphNode':
        self.fields[field] = val
        return self

    def value(self, field: str) -> Optional[Any]:
        return self.fields.get(field)

    def delete(self) -> 'GraphNode':
        self.is_deleted = True
        return self

    def comment(self, text: str) -> 'GraphNode':
        self.comment_text = text
        return self

    def set_comment(self, text: str):
        self.comment_text = text

    def id(self) -> Optional[Any]:
        return self.fields.get('id')

    def operation(self) -> Optional['EntityGraphOperation']:
        if self.is_deleted:
            return EntityGraphOperation.DELETE
        return EntityGraphOperation.SAVE

    def reference(self, rel: str, ref_id: Any) -> 'GraphNode':
        node = self.child(rel)
        node.set('id', ref_id)
        return node

class EntityGraphBuilder:
    def __init__(self, entity: str):
        self.node = GraphNode(entity)

    def set(self, key: str, value: Any) -> 'EntityGraphBuilder':
        self.node.set(key, value)
        return self

    def delete(self) -> 'EntityGraphBuilder':
        self.node.delete()
        return self

    def comment(self, text: str) -> 'EntityGraphBuilder':
        self.node.comment(text)
        return self

    def child(self, child_node: GraphNode) -> 'EntityGraphBuilder':
        self.node.children.append(child_node)
        return self

    def save(self) -> 'EntityGraphBuilder':
        self.node.operation = EntityGraphOperation.SAVE
        return self

    def build(self) -> GraphNode:
        return self.node

class EntityGraph:
    @staticmethod
    def new(entity: str) -> EntityGraphBuilder:
        return EntityGraphBuilder(entity)
