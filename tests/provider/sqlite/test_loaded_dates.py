from datetime import date

import pytest

from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.mutation import InsertCommand, MutationRequest, UpdateCommand
from teaql.core.query import SelectQuery
from teaql.core.value import DataType
from teaql.data_service import QueryRequest
from teaql.provider.sqlite import SimpleSchemaProvider, create_sqlite_service
from teaql.runtime import RuntimeModule


@pytest.mark.asyncio
async def test_declared_date_stays_native_across_save_query_and_stream(tmp_path):
    descriptor = EntityDescriptor('Visit').table_name('visit_data')
    descriptor.property(PropertyDescriptor('id', DataType.I64).is_id())
    descriptor.property(PropertyDescriptor('version', DataType.I64).is_version())
    descriptor.property(PropertyDescriptor('visit_date', DataType.Date))
    descriptor.property(PropertyDescriptor('date_label', DataType.Text))
    schema = SimpleSchemaProvider()
    schema.register_entity(descriptor)
    service = create_sqlite_service(str(tmp_path / 'dates.sqlite'), schema)
    context = RuntimeModule.new().entity(descriptor).into_context().with_schema_provider(service)
    await context.ensure_schema()
    inserted = await service.mutate(context, MutationRequest(
        InsertCommand.new('Visit').value('visit_date', date(2024, 2, 29)).value('date_label', '2024-02-29'),
        comment='create dated visit'))
    assert inserted.persisted_record['visit_date'] == date(2024, 2, 29)
    query = SelectQuery('Visit').comment('load dated visit').purpose('prove declared types')
    rows = (await service.query(context, QueryRequest(query))).rows
    assert rows[0]['visit_date'] == date(2024, 2, 29)
    assert rows[0]['date_label'] == '2024-02-29'
    chunks = [chunk async for chunk in service.query_stream(context, QueryRequest(query), 1)]
    assert chunks[0].rows[0]['visit_date'] == date(2024, 2, 29)
    sparse = (await service.query(context, QueryRequest(
        SelectQuery('Visit').project('id').comment('load visit identity').purpose('preserve sparse projection')))).rows
    assert 'visit_date' not in sparse[0]
    aggregate = (await service.query(context, QueryRequest(
        SelectQuery('Visit').count_field('id', 'visit_date').comment('count visits').purpose('retain aggregate type')))).rows
    assert aggregate[0]['visit_date'] == 1
    updated = await service.mutate(context, MutationRequest(
        UpdateCommand.new('Visit', rows[0]['id']).expected_version(rows[0]['version']).value('visit_date', None), comment='clear optional date'))
    assert updated.persisted_record['visit_date'] is None
    await service.close()
