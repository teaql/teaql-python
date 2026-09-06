from typing import Any, Dict, List
from .context import UserContext

class RuntimeModule:
    def __init__(self):
        self._entities: List[Any] = []
        self._behaviors: Dict[str, Any] = {}
        self._dependencies: Dict[str, Any] = {}
        self._audit_sinks: List[Any] = []
        self._checkers: Dict[str, Any] = {}
        self._generated_bootstraps: List[Any] = []
        self._schema_entities: List[Any] = []
        self._wire_metadata: Dict[str, Any] = {}

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

    def root_graph(self, graph_node: Any) -> 'RuntimeModule':
        """Register a create-if-absent root graph whose existing values are preserved."""
        if not hasattr(self, '_root_graphs'):
            self._root_graphs = []
        self._root_graphs.append(graph_node)
        return self

    def provide_custom_dependency(self, name: str, dependency: Any) -> 'RuntimeModule':
        self._dependencies[name] = dependency
        return self

    def audit_event_sink(self, sink: Any) -> 'RuntimeModule':
        self._audit_sinks.append(sink)
        return self

    def checker(self, entity: str, checker: Any) -> 'RuntimeModule':
        self._checkers[entity] = checker
        return self

    def generated_bootstrap(self, bootstrap: Any) -> 'RuntimeModule':
        """Register generated typed data bootstrap; invoked only by ensure_schema()."""
        self._generated_bootstraps.append(bootstrap)
        return self

    def wire_metadata(self, entity: str, metadata: Any) -> 'RuntimeModule':
        self._wire_metadata[entity] = metadata
        return self

    def schema_entity(self, descriptor: Any) -> 'RuntimeModule':
        """Register generated storage metadata without embedding a provider."""
        self._schema_entities.append(descriptor)
        return self

    def and_module(self, other: 'RuntimeModule') -> 'RuntimeModule':
        combined = RuntimeModule.new()
        combined._entities = [*self._entities, *other._entities]
        combined._behaviors = {**self._behaviors, **other._behaviors}
        combined._dependencies = {**self._dependencies, **other._dependencies}
        combined._audit_sinks = [*self._audit_sinks, *other._audit_sinks]
        combined._checkers = {**self._checkers, **other._checkers}
        combined._generated_bootstraps = [
            *self._generated_bootstraps,
            *other._generated_bootstraps,
        ]
        combined._schema_entities = [*self._schema_entities, *other._schema_entities]
        combined._wire_metadata = {**self._wire_metadata, **other._wire_metadata}
        combined._initial_graphs = [
            *getattr(self, '_initial_graphs', []),
            *getattr(other, '_initial_graphs', []),
        ]
        combined._root_graphs = [
            *getattr(self, '_root_graphs', []),
            *getattr(other, '_root_graphs', []),
        ]
        return combined

    def apply_to(self, context: UserContext):
        for name, dep in self._dependencies.items():
            context.insert_resource(name, dep)
        installed_entities = self._schema_entities or self._entities
        for entity in installed_entities:
            context.register_entity(entity)
        if hasattr(self, '_initial_graphs'):
            for graph in self._initial_graphs:
                context.add_initial_graph(graph)
        if hasattr(self, '_root_graphs'):
            for graph in self._root_graphs:
                context.add_root_graph(graph)
        context.insert_resource("entities", installed_entities)
        context.insert_resource("entity_classes", self._entities)
        context.insert_resource("behaviors", self._behaviors)
        context.insert_resource("wireMetadata", dict(self._wire_metadata))
        context.insert_resource("_teaql_generated_bootstraps", tuple(self._generated_bootstraps))
        if self._checkers:
            checkers = dict(self._checkers)
            class GeneratedCheckerRegistry:
                def checker(inner_self, entity):
                    return checkers.get(entity)
            context.set_checker_registry(GeneratedCheckerRegistry())
        if self._audit_sinks:
            sinks = tuple(self._audit_sinks)
            class CompositeSink:
                async def on_event(inner_self, context, event):
                    from .audit import deliver
                    for sink in sinks:
                        await deliver(sink, "on_event", context, event)
            context._set_standard_audit_sink(CompositeSink())

    def into_context(self) -> UserContext:
        context = UserContext.new()
        self.apply_to(context)
        return context

    async def configure(self, *args, **kwargs) -> UserContext:
        return self.into_context()

class DefaultEntityDataServiceBehavior:
    pass
