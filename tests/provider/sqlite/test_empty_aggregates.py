"""#236 EA-01..08: never confuse an absent contribution with a real zero."""

from copy import deepcopy
import json

import pytest

from teaql.core.expr import Expr
from teaql.core.meta import EntityDescriptor, PropertyDescriptor, RelationDescriptor
from teaql.core.mutation import InsertCommand, MutationRequest
from teaql.core.query import FacetRequest, RelationAggregate, SelectQuery
from teaql.core.value import DataType
from teaql.data_service import QueryRequest
from teaql.provider.sqlite import SimpleSchemaProvider, create_sqlite_service
from teaql.runtime import RuntimeModule


@pytest.mark.asyncio
async def test_empty_aggregates_preserve_null_zero_related_facets_and_json(tmp_path):
    bucket = EntityDescriptor("Bucket").table_name("ea_bucket")
    entry = EntityDescriptor("Entry").table_name("ea_entry")
    for entity in (bucket, entry):
        entity.property(PropertyDescriptor("id", DataType.I64).is_id())
        entity.property(PropertyDescriptor("version", DataType.I64).is_version())
    entry.property(PropertyDescriptor("bucket", DataType.I64))
    entry.property(PropertyDescriptor("amount", DataType.I64))
    bucket.relation(RelationDescriptor("entries", "Entry").foreign("bucket").many())
    entry.relation(RelationDescriptor("bucket", "Bucket").local("bucket").foreign("id"))
    schema = SimpleSchemaProvider()
    for entity in (bucket, entry):
        schema.register_entity(entity)
    service = create_sqlite_service(str(tmp_path / "empty.sqlite"), schema)
    context = RuntimeModule.new().entity(bucket).entity(entry).into_context().with_schema_provider(service)

    def bounded(entity):
        return SelectQuery(entity).limit(10).comment("inspect empty aggregates").purpose("verify EA-01 through EA-08")

    async def query(query):
        original = deepcopy(query)
        result = await service.query(context, QueryRequest(query))
        assert query == original
        return result

    try:
        await context.ensure_schema()
        for ident in range(1, 5):
            await service.mutate(context, MutationRequest(
                InsertCommand.new("Bucket").value("id", ident), comment="seed aggregate bucket"))
        for ident, owner, amount in [(1, 1, 4), (2, 1, -4), (3, 2, None), (4, 2, None),
                                     (5, 3, None), (6, 3, 2), (7, 3, -1), (8, 3, None)]:
            await service.mutate(context, MutationRequest(InsertCommand.new("Entry")
                .value("id", ident).value("bucket", owner).value("amount", amount), comment="seed aggregate contribution"))
        for owner, expected in [(4, (0, 0, None)), (2, (2, 0, None)), (3, (4, 2, 1)),
                                 (1, (2, 2, 0)), (None, (8, 4, 1))]:
            request = bounded("Entry").count("rows").count_field("amount", "values").sum("amount", "total")
            if owner is not None:
                request.filter(Expr.eq("bucket", owner))
            result = await query(request)
            assert len(result.rows) == 1
            row = result.rows[0]
            assert tuple(row[key] for key in ("rows", "values", "total")) == expected
            assert "total" in row and json.loads(json.dumps(row))["total"] == expected[2]
            explicit_default = row["total"] if row["total"] is not None else 0
            assert explicit_default == (expected[2] if expected[2] is not None else 0)
            assert row["total"] == expected[2]
        grouped = await query(bounded("Entry").filter(Expr.eq("bucket", 4)).group_by("bucket").sum("amount", "total"))
        assert grouped.rows == []

        parents = bounded("Bucket").order_asc("id")
        parents.relation_aggregates = [
            RelationAggregate("entries", "entry_count", bounded("Entry").count("count"), True),
            RelationAggregate("entries", "entry_total", bounded("Entry").sum("amount", "sum"), True),
        ]
        expected = [(1, 2, 0), (2, 2, None), (3, 4, 1), (4, 0, None)]
        related = await query(parents)
        assert [(r["id"], r["entry_count"], r["entry_total"]) for r in related.rows] == expected
        outer = bounded("Entry")
        choices = bounded("Bucket").order_asc("id").count("entry_count")
        choices.relation_aggregates = [parents.relation_aggregates[1]]
        outer.facets = [FacetRequest("buckets", "bucket", choices)]
        result = await query(outer)
        assert [(r["id"], r["entry_count"], r["entry_total"]) for r in result.facets["buckets"]] == expected
        print("EMPTY_AGGREGATES_PASS python sqlite EA-01..08")
    finally:
        await service.close()
