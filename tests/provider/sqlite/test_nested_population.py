"""Unbounded nested contributors must not inherit the outer materialization cap."""
from copy import deepcopy
import pytest
from teaql.core.expr import Expr
from teaql.core.meta import EntityDescriptor, PropertyDescriptor, RelationDescriptor
from teaql.core.query import FacetRequest, RelationAggregate, SelectQuery
from teaql.core.value import DataType
from teaql.data_service import QueryRequest
from teaql.provider.sqlite import SimpleSchemaProvider, create_sqlite_service
from teaql.runtime import RuntimeModule
from teaql.sql.types import CompiledQuery


def test_nested_population_ast_keeps_only_explicit_business_pages():
    child = SelectQuery("Entry")
    query = SelectQuery("Bucket").relation_query("entries", child)
    query.prepare_for_list()
    assert query.slice.limit == 10000
    assert child.slice is None
    explicit = SelectQuery("Entry").limit(2)
    SelectQuery("Bucket").relation_query("entries", explicit).prepare_for_list()
    assert explicit.slice.limit == 2


@pytest.mark.asyncio
async def test_nested_population_large_details_statistics_and_facets(tmp_path):
    bucket = EntityDescriptor("Bucket").table_name("np_bucket")
    entry = EntityDescriptor("Entry").table_name("np_entry")
    for entity in (bucket, entry):
        entity.property(PropertyDescriptor("id", DataType.I64).is_id())
        entity.property(PropertyDescriptor("version", DataType.I64).is_version())
    entry.property(PropertyDescriptor("bucket", DataType.I64))
    bucket.relation(RelationDescriptor("entries", "Entry").foreign("bucket").many())
    entry.relation(RelationDescriptor("bucket", "Bucket").local("bucket").foreign("id"))
    schema = SimpleSchemaProvider()
    for entity in (bucket, entry):
        schema.register_entity(entity)
    service = create_sqlite_service(str(tmp_path / "nested.sqlite"), schema)
    context = RuntimeModule.new().entity(bucket).entity(entry).into_context().with_schema_provider(service)
    context.disable_sql_log()
    def query(entity):
        return SelectQuery(entity).comment("inspect full nested population").purpose("prevent silent statistical truncation")
    try:
        await context.ensure_schema()
        # Native provider fixture only; all observations execute real query ASTs.
        for sql in [
            "WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM n WHERE x<10003) INSERT INTO np_bucket SELECT x,1 FROM n",
            "WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM n WHERE x<10003) INSERT INTO np_entry SELECT x,1,1 FROM n",
        ]:
            await service.transport.execute_sql(CompiledQuery(sql, []))
        root = query("Bucket").filter(Expr.eq("id", 1)).limit(1).relation_query("entries", query("Entry"))
        original = deepcopy(root)
        result = await service.query(context, QueryRequest(root))
        assert len(result.rows[0]["entries"]) == 10003
        assert root == original
        root = query("Bucket").filter(Expr.eq("id", 1)).limit(1)
        root.relation_aggregates = [RelationAggregate("entries", "n", query("Entry").count("n"), True)]
        result = await service.query(context, QueryRequest(root))
        assert result.rows[0]["n"] == 10003
        grouped = QueryRequest(query("Bucket").limit(1)).derive(query("Entry").group_by("id").count("n"), "entries")
        groups = (await service.query(context, grouped)).rows
        assert len(groups) == 10003
        assert sum(row["n"] for row in groups) == 10003
        page = await service.query(context, QueryRequest(query("Entry")))
        assert len(page.rows) == 10000
        root = query("Bucket").filter(Expr.eq("id", 1)).limit(1).relation_query("entries", query("Entry").order_asc("id").limit(2))
        assert len((await service.query(context, QueryRequest(root))).rows[0]["entries"]) == 2
        outer = query("Entry").limit(1)
        outer.facets = [FacetRequest("buckets", "bucket", query("Bucket").count("n"), True)]
        result = await service.query(context, QueryRequest(outer))
        assert len(result.facets["buckets"]) == 10003
    finally:
        await service.close()
