"""Native SQLite Blob binding in the caller's physical graph transaction."""

from teaql.core.blob_ref import BlobRef
from teaql.core.mutation import DeleteCommand, InsertCommand, UpdateCommand
from teaql.core.value import DataType, Value
from teaql.sql.types import CompiledQuery

from .sqlite_catalog import BlobBindingChange, BlobBindingTarget, SqliteBlobCatalog


class SqliteBlobMutationParticipant:
    def __init__(self, catalog: SqliteBlobCatalog, authorization):
        if not isinstance(catalog, SqliteBlobCatalog) or authorization is None or \
                not callable(getattr(authorization, "scope", None)) or \
                not callable(getattr(authorization, "authorize", None)):
            raise RuntimeError("BLOB_CAPABILITY_MISSING")
        self.catalog = catalog
        self.authorization = authorization

    async def apply(self, context, descriptor, mutation, persisted) -> None:
        graph = getattr(context, "_graph_session", None)
        if graph is None or context is not graph.context:
            raise RuntimeError("BLOB_TRANSACTION_REQUIRED")
        if not isinstance(mutation, (InsertCommand, UpdateCommand, DeleteCommand)):
            raise RuntimeError("BLOB_BIND_DENIED")
        id_property = next((prop for prop in descriptor.properties if prop._is_id), None)
        version_property = next((prop for prop in descriptor.properties if prop._is_version), None)
        if id_property is None or version_property is None:
            raise RuntimeError("BLOB_CAPABILITY_MISSING")
        if isinstance(mutation, DeleteCommand):
            raw_id = mutation.id.val
            action = "Delete"
        else:
            if not isinstance(persisted, dict):
                raise RuntimeError("BLOB_BIND_DENIED")
            raw_id = persisted.get(id_property.name)
            action = "Create" if isinstance(mutation, InsertCommand) else "Update"
        if isinstance(raw_id, bool) or not isinstance(raw_id, int) or raw_id <= 0:
            raise RuntimeError("BLOB_BIND_DENIED")
        entity_id = str(raw_id)
        try:
            scope = self.authorization.scope(context)
        except Exception:
            raise RuntimeError("BLOB_BIND_DENIED") from None
        if not isinstance(scope, str) or not scope or scope != scope.strip():
            raise RuntimeError("BLOB_BIND_DENIED")

        async def prior_version(target):
            async def query(sql):
                rows = await sql.fetch_all_sql(CompiledQuery(
                    "SELECT version FROM teaql_blob_binding WHERE scope = ? AND entity = ? "
                    "AND entity_id = ? AND field = ?",
                    [Value.Text(scope), Value.Text(target.entity), Value.Text(target.entity_id),
                     Value.Text(target.field)]))
                if len(rows) > 1:
                    raise RuntimeError("BLOB_CATALOG_FAILED")
                return rows[0]["version"] if rows else None
            return await graph.with_sql_transport(query)

        for prop in descriptor.properties:
            if prop.blob_spec is None:
                continue
            if prop.blob_spec.entity != descriptor._name or prop.blob_spec.field != prop.name:
                raise RuntimeError("BLOB_REFERENCE_INVALID")
            if action != "Delete" and prop.name not in mutation.values:
                if action == "Create" and not prop.blob_spec.nullable:
                    raise RuntimeError("BLOB_BIND_DENIED")
                if action != "Create":
                    continue
            target = BlobBindingTarget(descriptor._name, entity_id, prop.name)
            prior = await prior_version(target)
            if prior is not None and (type(prior) is not int or prior < 0):
                raise RuntimeError("BLOB_CATALOG_FAILED")
            if action == "Create" and prior is not None:
                raise RuntimeError("BLOB_BIND_DENIED")
            if action == "Delete":
                if prior is None:
                    raise RuntimeError("BLOB_BIND_DENIED")
                next_ref = None
            else:
                value = mutation.values.get(prop.name, Value.Null())
                if not isinstance(value, Value):
                    raise RuntimeError("BLOB_REFERENCE_INVALID")
                if value.val is None:
                    if not prop.blob_spec.nullable:
                        raise RuntimeError("BLOB_BIND_DENIED")
                    next_ref = None
                elif value._type_hint == DataType.BlobRef:
                    try:
                        next_ref = BlobRef.from_sql(value.val)
                    except ValueError:
                        raise RuntimeError("BLOB_REFERENCE_INVALID") from None
                else:
                    raise RuntimeError("BLOB_REFERENCE_INVALID")
                if persisted.get(prop.name) != (next_ref.key if next_ref else None):
                    raise RuntimeError("BLOB_BIND_DENIED")
            business_version = persisted.get(version_property.name) if persisted else None
            next_version = max((prior or 0) + 1,
                               business_version if type(business_version) is int and business_version > 0 else 0)
            await self.catalog.bind_in_graph(graph, context,
                BlobBindingChange(target, next_ref, prior or 0, next_version, action),
                self.authorization)
