"""Native SQLite integration for the typed-list runtime bridge, not generated-code evidence."""
from dataclasses import dataclass
from decimal import Decimal
import json
from pathlib import Path

import aiosqlite
import pytest

from teaql.core.expr import Expr
from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.query import SelectQuery
from teaql.core.request_tree import QueryOperation
from teaql.core.value import DataType
from teaql.data_service import QueryRequest
from teaql.provider.sqlite import SimpleSchemaProvider
from teaql.provider.sqlite.dialect import SqliteDialect
from teaql.provider.sqlite.transport import SqliteTransport
from teaql.runtime import RuntimeModule
from teaql.runtime.query_list import execute_typed_list
from teaql.sql.executor import SqlDataServiceExecutor

VECTORS = json.loads((Path(__file__).parents[2] / 'fixtures/smart-list-semantics.json').read_text())


@dataclass
class NativeOrder:
    id: int
    version: int
    status: str
    amount: Decimal


@pytest.fixture
async def context(tmp_path):
    descriptor = EntityDescriptor('Order').table_name('orders')
    descriptor.property(PropertyDescriptor('id', DataType.I64).is_id())
    descriptor.property(PropertyDescriptor('version', DataType.I64).is_version())
    descriptor.property(PropertyDescriptor('status', DataType.Text))
    descriptor.property(PropertyDescriptor('amount', DataType.Decimal))
    schema = SimpleSchemaProvider()
    schema.register_entity(descriptor)
    module = RuntimeModule.new().entity(descriptor)
    result = module.into_context()
    path = str(tmp_path / 'smart-list.sqlite')
    service = SqlDataServiceExecutor(SqliteDialect(), SqliteTransport(path), schema)
    result.insert_resource('dataService', service)
    async with aiosqlite.connect(path) as db:
        await db.execute('CREATE TABLE orders (id INTEGER PRIMARY KEY, version INTEGER, status TEXT, amount NUMERIC)')
        await db.executemany('INSERT INTO orders VALUES (?, 1, ?, ?)',
                             [(row['id'], row['status'], row['amount']) for row in VECTORS['sqlite']['rows']])
        await db.commit()
    return result


def request():
    return SelectQuery('Order').comment('read shared SmartList fixture').purpose('verify native SQLite semantics')


@pytest.mark.asyncio
async def test_sqlite_unknown_zero_and_page_totals_remain_distinct(context):
    unknown = await execute_typed_list(context, QueryRequest(request().limit(1)), lambda row: NativeOrder(**row))
    assert len(unknown) == 1 and isinstance(unknown[0], NativeOrder)
    assert unknown.is_loaded and unknown.total_count is None
    page = VECTORS['sqlite']
    query = request().order_asc('id').offset(page['pageOffset']).limit(page['pageLimit']).count_field('id', 'n')
    result = await execute_typed_list(context, QueryRequest(query), lambda row: NativeOrder(**row),
                                    count_operation=QueryOperation('named-count', 'count_as', 'n'), count_alias='n')
    assert [row.id for row in result] == page['pageIds']
    assert result.total_count == page['total'] and result.aggregations == {'n': page['total']}
    empty = request().filter(Expr.eq('status', page['emptyStatus'])).limit(1)
    result = await execute_typed_list(context, QueryRequest(empty), lambda row: NativeOrder(**row))
    assert result == [] and result.total_count is None and result.is_loaded
    result = await execute_typed_list(context, QueryRequest(empty.count_field('id', 'n')),
                                    lambda row: NativeOrder(**row),
                                    count_operation=QueryOperation('named-count', 'count_as', 'n'), count_alias='n')
    assert result == [] and result.total_count == 0 and result.aggregations == {'n': 0}


@pytest.mark.asyncio
async def test_sqlite_scalar_aggregations_remain_metadata_without_entity_rows(context):
    query = request().sum('amount', 'amountTotal')

    def forbidden(row):
        pytest.fail('scalar SQL aggregation cannot be hydrated as NativeOrder')

    result = await execute_typed_list(context, QueryRequest(query), forbidden)
    assert result == [] and result.total_count is None and result.is_loaded
    assert result.aggregations == {'amountTotal': Decimal(VECTORS['sqlite']['sumAmount'])}
