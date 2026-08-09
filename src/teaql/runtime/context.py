from typing import Dict, Any, Optional, List

class UserContext:
    def __init__(self):
        self._resources: Dict[str, Any] = {}
        self._metadata: Optional[Any] = None
        self._user_identifier: str = ""
        self._entities: List[Any] = []
        self._initial_graphs: List[Any] = []

    @classmethod
    def new(cls) -> 'UserContext':
        return cls()
        
    def register_entity(self, entity_desc: Any):
        self._entities.append(entity_desc)
        
    def all_entities(self) -> List[Any]:
        return self._entities
        
    def add_initial_graph(self, graph_node: Any):
        self._initial_graphs.append(graph_node)
        
    def initial_graphs(self) -> List[Any]:
        return self._initial_graphs

    def with_metadata(self, metadata: Any) -> 'UserContext':
        self._metadata = metadata
        return self

    def insert_resource(self, resource_type: str, resource: Any):
        self._resources[resource_type] = resource

    def get_resource(self, resource_type: str) -> Optional[Any]:
        return self._resources.get(resource_type)
        
    def require_resource(self, resource_type: str) -> Any:
        res = self._resources.get(resource_type)
        if res is None:
            raise Exception(f"Resource {resource_type} not found")
        return res

    def set_user_identifier(self, identifier: str):
        self._user_identifier = identifier

    def user_identifier(self) -> str:
        return self._user_identifier


class TeaqlRuntime:
    def __init__(self, ctx: UserContext):
        self._ctx = ctx

    @property
    def context(self) -> UserContext:
        return self._ctx

    def get_service(self, name: str) -> Optional[Any]:
        return self._ctx.get_resource(name)

    def require_service(self, name: str) -> Any:
        return self._ctx.require_resource(name)
