import pytest

from teaql.core.expr import BinaryExpr, BinaryOp
from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.query import SelectQuery
from teaql.core.value import DataType
from teaql.data_service import QueryRequest
from teaql.runtime.context import UserContext
from teaql.sql.executor import SchemaProvider, SqlDataServiceExecutor, SqlTransport
from teaql.sql.types import DatabaseKind
from teaql.sql.dialect import SqlDialect


class Dialect(SqlDialect):
    def kind(self): return DatabaseKind.PostgreSql
    def quote_ident(self, ident): return f'"{ident}"'
    def placeholder(self, index): return f'${index}'


class Schema(SchemaProvider):
    def __init__(self):
        self.order = EntityDescriptor("Order").table_name("orders")
        self.order.property(PropertyDescriptor("id", DataType.U64).column_name("id").is_id())
    def get_entity(self, name): return self.order if name == "Order" else None


class Transport(SqlTransport):
    def __init__(self, pages):
        self.pages = list(pages)
        self.compiled = []
    async def fetch_all_sql(self, query):
        self.compiled.append(query)
        return self.pages.pop(0)
    async def execute_sql(self, query): return 0


class UnavailableStore:
    async def get(self, query_key, target_offset): raise RuntimeError("store unavailable")
    async def put(self, cursor): raise RuntimeError("store unavailable")
    async def invalidate(self, query_key): raise RuntimeError("store unavailable")


def rows(start, descending=True):
    return [{"id": start - i if descending else start + i} for i in range(10)]


@pytest.mark.asyncio
async def test_descending_and_ascending_next_pages_use_seek():
    for descending in (True, False):
        transport = Transport([rows(100 if descending else 1, descending), rows(90 if descending else 11, descending)])
        executor = SqlDataServiceExecutor(Dialect(), transport, Schema())
        ctx = UserContext().with_user_identifier("tenant-1:user-1")
        for offset in (0, 10):
            query = SelectQuery("Order")
            (query.order_desc("id") if descending else query.order_asc("id"))
            query.offset(offset).limit(10).optimize_for_continuous_page_fetch_with("orders", 60)
            await executor.query(ctx, QueryRequest(query).comment("browse").purpose("browse orders"))
        assert ctx.continuous_page_plan() == "CURSOR_SEEK"
        assert ctx.continuous_page_cursor_id()
        sql = transport.compiled[1].sql
        assert "OFFSET 10" not in sql
        assert ('"id" <' in sql) if descending else ('"id" >' in sql)


@pytest.mark.asyncio
async def test_missing_cursor_and_store_outage_fall_back():
    transport = Transport([rows(90), rows(80)])
    executor = SqlDataServiceExecutor(Dialect(), transport, Schema())
    ctx = UserContext()
    query = SelectQuery("Order").order_desc("id").offset(10).limit(10).optimize_for_continuous_page_fetch_with("missing", 60)
    await executor.query(ctx, QueryRequest(query).comment("browse").purpose("browse orders"))
    assert ctx.continuous_page_plan() == "OFFSET_FALLBACK:CACHE_MISS"
    ctx.set_continuous_page_cursor_store(UnavailableStore())
    query = SelectQuery("Order").order_desc("id").offset(10).limit(10).optimize_for_continuous_page_fetch_with("outage", 60)
    await executor.query(ctx, QueryRequest(query).comment("browse").purpose("browse orders"))
    assert ctx.continuous_page_plan() == "OFFSET_FALLBACK:STORE_UNAVAILABLE"
