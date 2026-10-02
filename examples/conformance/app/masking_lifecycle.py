"""Runtime-owned fixture; does not modify generated domain-library code."""
from contextlib import aclosing
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from teaql.core.expr import Expr
from teaql.core.meta import EntityDescriptor, PropertyDescriptor, RelationDescriptor
from teaql.core.mutation import InsertCommand, MutationRequest, TraceNode
from teaql.core.query import SelectQuery
from teaql.core.value import DataType
from teaql.data_service import QueryRequest
from teaql.provider.sqlite import SimpleSchemaProvider, create_sqlite_service
from teaql.runtime import RuntimeModule
from teaql.runtime.context import TextDiagnosticSqlLogSink
from teaql.sql.executor import TransportError
from teaql.sql.types import CompiledQuery


async def verify_masking_lifecycle():
    with TemporaryDirectory(prefix='teaql-mask-lifecycle-') as directory:
        entity = (EntityDescriptor('MaskCustomer').table_name('mask_customer_data')
                  .property(PropertyDescriptor('id', DataType.I64).is_id())
                  .property(PropertyDescriptor('version', DataType.I64).is_version())
                  .property(PropertyDescriptor('display_name', DataType.Text))
                  .audit_mask_fields(['display_name']))
        entity.relation(RelationDescriptor('children', 'MaskChild').foreign('parent_id').many())
        child = (EntityDescriptor('MaskChild').table_name('mask_child_data')
                 .property(PropertyDescriptor('id', DataType.I64).is_id())
                 .property(PropertyDescriptor('version', DataType.I64).is_version())
                 .property(PropertyDescriptor('parent_id', DataType.I64)))
        provider = SimpleSchemaProvider()
        provider.register_entity(entity)
        provider.register_entity(child)
        service = create_sqlite_service(str(Path(directory) / 'mask.sqlite'), provider)
        context = RuntimeModule.new().entity(entity).entity(child).into_context().with_schema_provider(service)
        await context.ensure_schema()
        output, entries = [], []
        log_file = Path(directory) / 'sql.log'
        def write_line(text):
            output.append(text)
            with log_file.open('a', encoding='utf-8') as destination:
                destination.write(text + '\n')
        sink = TextDiagnosticSqlLogSink(write_line)
        def capture(entry):
            entries.append(entry)
            sink.write(entry)
        context.set_diagnostic_sql_log_sink(SimpleNamespace(write=capture))
        async def insert(entity_id, target=None, request_context=None):
            command = (InsertCommand('MaskCustomer').value('id', entity_id).value('version', 1)
                       .value('display_name', 'Riverside'))
            command.trace_chain = [TraceNode(comment='what: seed Riverside lifecycle fixture')]
            return await (target or service).mutate(request_context or context, MutationRequest(command, comment='what: seed Riverside lifecycle fixture'))
        try:
            for entity_id in [1, 2, 3]:
                await insert(entity_id)
            entries.clear()
            output.clear()
            request = QueryRequest(SelectQuery('MaskCustomer')
                .filter(Expr.eq('display_name', 'Riverside')).limit(3)
            , _comment='what: runtime regression fixture', _purpose='why: verify runtime behavior').comment('what: inspect customers').purpose('why: verify stream lifecycle')
            # async-for break alone does not promise immediate generator close
            # in Python. aclosing makes ownership explicit and deterministic.
            async with aclosing(service.query_stream(context, request, 1)) as stream:
                async for chunk in stream:
                    assert chunk.rows[0]['display_name'] == 'Riverside'
                    break
            assert len(entries) == 1 and entries[0].execution_outcome == 'cancelled'
            assert entries[0].result_count == 1
            try:
                await insert(1)
                raise AssertionError('duplicate key unexpectedly succeeded')
            except TransportError:
                pass
            assert entries[-1].execution_outcome == 'failure'
            assert entries[-1].affected_rows is None
            result = await service.query(context, request)
            assert len(result.rows) == 3
            assert all(row['display_name'] == 'Riverside' for row in result.rows)
            assert entries[-1].execution_outcome == 'success'
            text = '\n'.join(output)
            assert 'Riverside' not in text and 'Ri*****de' in text
            assert 'what: inspect customers' in text and 'why: verify stream lifecycle' in text

            await service.transport.execute_sql(CompiledQuery(
                'CREATE TRIGGER remove_mask_probe AFTER INSERT ON mask_customer_data '
                'WHEN NEW.id = 777 BEGIN DELETE FROM mask_customer_data WHERE id = NEW.id; END', []))
            entries.clear()
            output.clear()
            try:
                await insert(777)
                raise AssertionError('missing snapshot unexpectedly succeeded')
            except TransportError:
                pass
            assert len(entries) == 2
            assert entries[0].execution_outcome == 'success' and entries[0].affected_rows == 1
            assert entries[1].execution_outcome == 'success' and entries[1].result_count == 0
            assert 'what: seed' in entries[1].audit_reason
            assert 'Riverside' not in repr(entries) and 'Riverside' not in '\n'.join(output)

            context.insert_resource('dataService', service)
            entries.clear()
            async def partial_graph(graph):
                await insert(30, graph.transaction, graph.context)
                await insert(777, graph.transaction, graph.context)
                await insert(31, graph.transaction, graph.context)
            try:
                await context.execute_graph_save(partial_graph, comment='what: runtime regression fixture')
                raise AssertionError('partial graph unexpectedly committed')
            except TransportError:
                pass
            assert [entry.execution_outcome for entry in entries] == ['success','success','success']
            assert entries[-1].result_count == 0
            assert not await service.transport.fetch_all_sql(CompiledQuery(
                'SELECT id FROM mask_customer_data WHERE id IN (30,31,777)', []))
            assert 'Riverside' not in repr(entries)
            await insert(32)
            assert len(await service.transport.fetch_all_sql(CompiledQuery('SELECT id FROM mask_customer_data', []))) == 4

            command = (InsertCommand('MaskChild').value('id', 1).value('version', 1).value('parent_id', 1))
            command.trace_chain = [TraceNode(comment='what: seed child for relation verification')]
            await service.mutate(context, MutationRequest(command, comment='what: runtime regression fixture'))
            graph_request = QueryRequest(SelectQuery('MaskCustomer').project('id')
                .filter(Expr.eq('id', 1)).and_filter(Expr.eq('display_name', 'Riverside'))
                .relation_query('children', SelectQuery('MaskChild').project('id').limit(2)).limit(1)
            , _comment='what: runtime regression fixture', _purpose='why: verify runtime behavior').comment('what: load Riverside graph').purpose('why: verify inherited relation masking')
            entries.clear()
            await service.transport.execute_sql(CompiledQuery(
                'ALTER TABLE mask_child_data RENAME TO mask_child_unavailable', []))
            try:
                try:
                    await service.query(context, graph_request)
                    raise AssertionError('missing relation table unexpectedly succeeded')
                except TransportError:
                    pass
            finally:
                await service.transport.execute_sql(CompiledQuery(
                    'ALTER TABLE mask_child_unavailable RENAME TO mask_child_data', []))
            assert [entry.execution_outcome for entry in entries] == ['success', 'failure']
            assert 'what: load' in entries[-1].comment
            assert 'mask_child_data' in entries[-1].debug_sql
            assert 'Riverside' not in repr(entries) + log_file.read_text(encoding='utf-8')
            restored = await service.query(context, graph_request)
            assert restored.rows[0]['children'][0]['id'] == 1
        finally:
            await service.close()
    print('PASS Python masked SQL lifecycle: stream, readback intent, SQLite failure, partial graph rollback, relation file/custom sinks and reuse')
