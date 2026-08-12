from typing import Any, Dict, List
from .context import UserContext

class RuntimeModule:
    def __init__(self):
        self._entities: List[Any] = []
        self._behaviors: Dict[str, Any] = {}
        self._dependencies: Dict[str, Any] = {}
        self._audit_sinks: List[Any] = []

    @classmethod
    def new(cls) -> 'RuntimeModule':
        return cls()

    def entity(self, entity_class: Any) -> 'RuntimeModule':
        self._entities.append(entity_class)
        return self

    def entity_with_behavior(self, entity_class: Any, behavior: Any) -> 'RuntimeModule':
        self._entities.append(entity_class)
        name = getattr(entity_class, '_name', getattr(entity_class, '__name__', str(entity_class)))
        self._behaviors[name] = behavior
        return self
        
    def initial_graph(self, graph_node: Any) -> 'RuntimeModule':
        if not hasattr(self, '_initial_graphs'):
            self._initial_graphs = []
        self._initial_graphs.append(graph_node)
        return self

    def provide_custom_dependency(self, name: str, dependency: Any) -> 'RuntimeModule':
        self._dependencies[name] = dependency
        return self

    def audit_event_sink(self, sink: Any) -> 'RuntimeModule':
        self._audit_sinks.append(sink)
        return self

    def apply_to(self, ctx: UserContext):
        for name, dep in self._dependencies.items():
            ctx.insert_resource(name, dep)
        for entity in self._entities:
            ctx.register_entity(entity)
        if hasattr(self, '_initial_graphs'):
            for graph in self._initial_graphs:
                ctx.add_initial_graph(graph)
        ctx.insert_resource("entities", self._entities)
        ctx.insert_resource("behaviors", self._behaviors)
        if self._audit_sinks:
            sinks = tuple(self._audit_sinks)
            class CompositeSink:
                async def on_event(inner_self, context, event):
                    from .audit import deliver
                    for sink in sinks:
                        await deliver(sink, "on_event", context, event)
            ctx._set_standard_audit_sink(CompositeSink())

    def into_context(self) -> UserContext:
        ctx = UserContext.new()
        self.apply_to(ctx)
        return ctx

    async def configure(self, *args, **kwargs) -> UserContext:
        return self.into_context()

class DefaultEntityDataServiceBehavior:
    pass
