"""Authorize read-only query aliases at the typed hydration boundary.

No Context, provider, identity allocator or mutation ledger is touched. Staging
the whole selected graph prevents a later error from partially changing views.
"""
from teaql.core.projection_properties import ProjectionProperties
from .entity_json import EntityJSONError
from .i18n import ObjectLocation


def capture_entity_query_properties(entity, query):
    staged, visited = [], set()

    def visit(node, selected, depth):
        if depth > 64:
            raise ValueError("Selected query-property graph exceeds the depth limit")
        identity = (id(node), id(selected))
        if identity in visited:
            return
        visited.add(identity)
        schema = getattr(type(node), "_teaql_json_schema", None)
        properties = getattr(node, "_projection_properties", None)
        if schema is None or not isinstance(properties, ProjectionProperties):
            return  # Existing custom hydrators retain their native result type.
        names = [item.alias for item in (*selected.aggregates, *selected.relation_aggregates)]
        names.extend(item.alias for item in selected.expr_projection)
        names.extend(item.property_name for item in (*selected.raw_projections, *selected.dynamic_properties))
        for name in names:
            if (not isinstance(name, str) or not name or len(name) > 4096
                    or name in schema._query_reserved_names()):
                raise EntityJSONError("WIRE_QUERY_PROPERTY_COLLISION", ObjectLocation(), "",
                                      "Query alias conflicts with the model namespace")
        if len(names) != len(set(names)):
            raise ValueError("Duplicate selected query-property alias")
        view = properties.with_selected_aliases(names)
        if view is not properties:
            staged.append((node, view))
        fields = {field.canonical_name: field for field in schema.fields}
        loaded = getattr(node, "_loaded_fields", ())
        for relation in selected.relations:
            field = fields.get(relation.name)
            if (field is None or relation.query is None
                    or (field.loaded_name or field.native_name) not in loaded):
                continue
            value = getattr(node, field.native_name)
            if value is None:
                continue
            children = value if field.kind == "many" else (value,)
            for child in children:
                visit(child, relation.query, depth + 1)

    visit(entity, query, 0)
    for node, view in staged:
        node._projection_properties = view
    return entity


def invalidate_committed_query_properties(entity):
    """A real write cannot return old derived values as authoritative readback.

    Do not recompute expressions or query here. Only the actually prepared
    entity loses this old snapshot; unchanged views and rollback paths keep it.
    """
    if isinstance(getattr(entity, "_projection_properties", None), ProjectionProperties):
        entity._projection_properties = ProjectionProperties({}, ())
