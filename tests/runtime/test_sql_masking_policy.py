from dataclasses import replace
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from teaql.core.expr import Expr
from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.mutation import InsertCommand, UpdateCommand, DeleteCommand, MutationRequest, TraceNode
from teaql.core.query import SelectQuery
from teaql.core.value import DataType, Value
from teaql.data_service import QueryRequest
from teaql.provider.sqlite import create_sqlite_service, SimpleSchemaProvider
from teaql.provider.postgres.dialect import PostgresDialect
from teaql.runtime import RuntimeModule
from teaql.runtime.context import SqlLogEntry, SqlLogOperation, TextDiagnosticSqlLogSink
from teaql.runtime.log_privacy import PLAINTEXT_ENV, PLAINTEXT_ACK, sql_log_projection
from teaql.sql.types import DatabaseKind


@pytest.fixture(autouse=True)
def safe_environment(monkeypatch):
    monkeypatch.delenv(PLAINTEXT_ENV, raising=False)


def entry(sql, params, **kwargs):
    return SqlLogEntry(SqlLogOperation.Select, 'what: read customers', 'why: test policies', None,
                       [], sql, params, '', '', datetime.now(), datetime.now(), timedelta(microseconds=1),
                       1, None, None, '1 rows returned', **kwargs)


def test_mixed_policies_repeated_binds_and_projection_copy():
    raw = entry('SELECT $1, $2, $1', [Value.Text("O'Reilly"), Value.Bool(True)],
                database_kind=DatabaseKind.PostgreSql, parameter_log_policies=['masked', 'plain'])
    safe = sql_log_projection(raw)
    assert "'O''****ly' /* masked */, TRUE, 'O''****ly' /* masked */" in safe.debug_sql
    assert safe.masked_parameters == [True, False]
    assert sql_log_projection(safe) is safe
    assert raw.params[0].val == "O'Reilly"
    safe.params[1]._data = False
    assert raw.params[1].val is True
    assert 'FALSE' in sql_log_projection(safe).debug_sql


@pytest.mark.parametrize('value', [1, 'customer'])
def test_copied_projection_keeps_compiled_sql_structure(value):
    sql = 'SELECT id FROM customer WHERE name = ? LIMIT 10000'
    safe = sql_log_projection(entry(sql, [value], sql_origin='generated'))
    assert safe.sql == sql
    assert 'FROM customer' in sql_log_projection(replace(safe)).debug_sql
    assert 'LIMIT 10000' in sql_log_projection(replace(safe)).debug_sql


@pytest.mark.parametrize('debug', [False, True])
def test_inherited_intent_never_retains_raw_source(monkeypatch, debug):
    from dataclasses import asdict
    from teaql.sql.types import CompiledQuery
    if debug:
        monkeypatch.setenv(PLAINTEXT_ENV, PLAINTEXT_ACK)
    source = CompiledQuery('UPDATE customer SET a=?, b=?, c=?, d=?',
        ['Riverside', 'UNKNOWN-CANARY', {'api_key':'NESTED-CANARY'}, 12345.0],
        parameter_log_policies=['masked','unknown','plain','masked'], sql_origin='generated')
    raw = entry('SELECT id FROM customer WHERE id=?', [1],
                parameter_log_policies=['plain'], sql_origin='generated')
    raw.audit_reason = 'what: update Riverside UNKNOWN-CANARY NESTED-CANARY 12345.0'
    raw.trace_path = [TraceNode(comment=raw.audit_reason)]
    safe = sql_log_projection(raw, _intent_source=source)
    assert ('Riverside' in safe.audit_reason) == debug
    assert ('12345.0' in safe.audit_reason) == debug
    for secret in ['UNKNOWN-CANARY','NESTED-CANARY']:
        assert secret not in repr(asdict(safe))
    assert '_intent_source' not in vars(safe)
    assert source.params[0] == 'Riverside'
    if not debug:
        monkeypatch.setenv(PLAINTEXT_ENV, PLAINTEXT_ACK)
        assert 'Riverside' not in repr(sql_log_projection(replace(safe)))
        assert sql_log_projection(replace(safe)).log_mode == 'masked'


@pytest.mark.parametrize('sql', ['SELECT $0', 'SELECT $2', 'SELECT ?, ?', 'SELECT 1', ''])
def test_invalid_bindings_are_omitted_with_reason(sql):
    safe = sql_log_projection(entry(sql, ['BIND-CANARY']))
    assert safe.omission_reason is not None
    assert safe.debug_sql == '[REDACTED SQL; NOT REPLAYABLE]'
    assert 'BIND-CANARY' not in repr(safe)


def test_trusted_literals_and_backticks_ignore_false_placeholders():
    safe = sql_log_projection(entry("SELECT `field?`, 'fixed?', ? /* fixed ? */", ['Riverside'],
                              sql_origin='generated', parameter_log_policies=['masked']))
    assert "`field?`, 'fixed?', 'Ri*****de' /* masked */" in safe.debug_sql


def test_compiled_postgres_kind_and_field_policy_reach_dialect_renderer():
    dialect = PostgresDialect()
    entity = (EntityDescriptor('Customer').property(PropertyDescriptor('display_name', DataType.Text))
              .audit_mask_fields(['display_name']))
    compiled = dialect.compile_select(entity, SelectQuery('Customer')
                                      .filter(Expr.eq('display_name', 'Riverside')).limit(2))
    safe = sql_log_projection(entry(compiled.sql, compiled.params, database_kind=dialect.kind(),
                                   parameter_log_policies=compiled.parameter_log_policies,
                                   sql_origin=compiled.sql_origin))
    assert 'Ri*****de' in safe.debug_sql
    assert 'Riverside' not in repr(safe)
    assert safe.omission_reason is None


def test_legacy_missing_mask_metadata_overrides_old_plain_property_policy():
    from teaql.provider.sqlite.dialect import SqliteDialect
    entity = EntityDescriptor('Customer').table_name('customer_data')
    entity.property(PropertyDescriptor('name', DataType.Text).log_policy('plain'))
    query = SelectQuery('Customer').filter(Expr.eq('name', 'PRIVATE-CANARY')).limit(1)
    dialect = SqliteDialect()
    compiled = dialect.compile_select(entity, query)
    assert compiled.parameter_log_policies == ['unknown']
    safe = sql_log_projection(entry(compiled.sql, compiled.params,
                                    sql_origin=compiled.sql_origin,
                                    parameter_log_policies=compiled.parameter_log_policies))
    assert 'PRIVATE-CANARY' not in repr(safe)
    assert '[REDACTED]' in safe.debug_sql
    entity.audit_mask_fields([])
    declared = dialect.compile_select(entity, query)
    assert declared.parameter_log_policies == ['plain']


def test_mysql_log_renderer_uses_masks_and_skips_quoted_placeholders():
    safe = sql_log_projection(entry('SELECT `col%s`, %s, %s', ['Riverside', True],
                                   database_kind=DatabaseKind.MySql, sql_origin='generated',
                                   parameter_log_policies=['masked', 'plain']))
    assert "`col%s`, 'Ri*****de' /* masked */, TRUE" in safe.debug_sql
    assert safe.omission_reason is None


def test_debug_never_reveals_inline_or_bound_credentials(monkeypatch):
    monkeypatch.setenv(PLAINTEXT_ENV, PLAINTEXT_ACK)
    raw = entry('UPDATE users SET password = ?', ['CREDENTIAL-CANARY'], parameter_log_policies=['plain'])
    assert 'CREDENTIAL-CANARY' not in repr(sql_log_projection(raw))
    raw = entry("UPDATE users SET password = 'CREDENTIAL-CANARY'", [])
    safe = sql_log_projection(raw)
    assert 'CREDENTIAL-CANARY' not in repr(safe)
    assert safe.omission_reason == 'untrusted-literal-sql'


@pytest.mark.parametrize('debug', [False, True])
def test_generated_credential_column_does_not_override_other_field_policies(monkeypatch, debug):
    from teaql.provider.sqlite.dialect import SqliteDialect
    if debug:
        monkeypatch.setenv(PLAINTEXT_ENV, PLAINTEXT_ACK)
    entity = EntityDescriptor('Customer').table_name('customer_data')
    for field in ['display_name', 'public_address', 'password_hash']:
        entity.property(PropertyDescriptor(field, DataType.Text).log_policy('plain'))
    entity.audit_mask_fields(['display_name', 'password_hash'])
    compiled = SqliteDialect().compile_select(entity, SelectQuery('Customer')
        .filter(Expr.eq('display_name', 'Riverside'))
        .and_filter(Expr.eq('public_address', '1 Runtime Road'))
        .and_filter(Expr.eq('password_hash', 'PASSWORD-CANARY')).limit(1))
    raw = entry(compiled.sql, compiled.params, sql_origin=compiled.sql_origin,
                parameter_log_policies=compiled.parameter_log_policies)
    safe = sql_log_projection(raw)
    assert safe.parameter_log_policies == ['masked', 'plain', 'credential']
    assert ('Riverside' if debug else 'Ri*****de') in safe.debug_sql
    assert '1 Runtime Road' in safe.debug_sql
    assert 'PASSWORD-CANARY' not in repr(safe)
    output = []
    TextDiagnosticSqlLogSink(output.append).write(safe)
    assert safe.debug_sql in output[0]
    assert raw.params[2].val == 'PASSWORD-CANARY'


@pytest.mark.parametrize('policies', [None, ['unknown'], ['unsupported-policy']])
def test_debug_never_exposes_unclassified_bindings(monkeypatch, policies):
    monkeypatch.setenv(PLAINTEXT_ENV, PLAINTEXT_ACK)
    raw = entry('SELECT ?', ['UNKNOWN-BINDING-CANARY'], parameter_log_policies=policies)
    raw.comment = 'what: locate UNKNOWN-BINDING-CANARY'
    safe = sql_log_projection(raw)
    assert 'UNKNOWN-BINDING-CANARY' not in repr(safe)
    assert safe.masked_parameters == [True]
    assert 'SELECT' in safe.debug_sql and 'NOT REPLAYABLE' in safe.debug_sql
    assert raw.params == ['UNKNOWN-BINDING-CANARY']


def test_debug_only_exposes_explicit_business_policies(monkeypatch):
    monkeypatch.setenv(PLAINTEXT_ENV, PLAINTEXT_ACK)
    safe = sql_log_projection(entry('SELECT ?, ?, ?, ?',
        ['Ordinary', 'Riverside', 'UNKNOWN-BINDING-CANARY', 'CREDENTIAL-CANARY'],
        parameter_log_policies=['plain', 'masked', 'unknown', 'credential']))
    assert safe.params == ['Ordinary', 'Riverside', '[REDACTED]', '[REDACTED]']
    assert safe.masked_parameters == [False, False, True, True]


def test_debug_disabled_reprojects_without_recovering_plaintext(monkeypatch):
    monkeypatch.setenv(PLAINTEXT_ENV, PLAINTEXT_ACK)
    debug = sql_log_projection(entry('SELECT ?', ['Riverside'], parameter_log_policies=['masked']))
    assert 'Riverside' in debug.debug_sql
    monkeypatch.delenv(PLAINTEXT_ENV)
    safe = sql_log_projection(debug)
    assert 'Riverside' not in repr(safe)
    monkeypatch.setenv(PLAINTEXT_ENV, PLAINTEXT_ACK)
    assert sql_log_projection(safe) is safe


@pytest.mark.asyncio
async def test_sqlite_crud_routes_compiler_policies_before_every_sink(tmp_path):
    entity = (EntityDescriptor('Customer').table_name('customer_data')
              .property(PropertyDescriptor('id', DataType.I64).is_id())
              .property(PropertyDescriptor('version', DataType.I64).is_version())
              .property(PropertyDescriptor('display_name', DataType.Text))
              .property(PropertyDescriptor('active', DataType.Bool).log_policy('plain'))
              .audit_mask_fields(['display_name']))
    provider = SimpleSchemaProvider()
    provider.register_entity(entity)
    service = create_sqlite_service(str(tmp_path / 'mask.db'), provider)
    context = RuntimeModule.new().entity(entity).into_context().with_schema_provider(service)
    await context.ensure_schema()
    entries, output = [], []
    sink = TextDiagnosticSqlLogSink(output.append)
    def capture(log):
        entries.append(log)
        sink.write(log)
    context.set_diagnostic_sql_log_sink(SimpleNamespace(write=capture))
    async def mutate(command):
        command.trace_chain = [TraceNode(comment='what: verify mutation log policy')]
        return await service.mutate(context, MutationRequest(command, comment='what: runtime regression fixture'))
    await mutate(InsertCommand('Customer').value('id', 1).value('version', 1)
                 .value('display_name', 'Riverside').value('active', True))
    query = SelectQuery('Customer').filter(Expr.new_and(
        Expr.eq('display_name', 'Riverside'), Expr.eq('active', True))).limit(1)
    rows = (await service.query(context, QueryRequest(query, _comment='what: runtime regression fixture', _purpose='why: verify runtime behavior')
            .comment('what: read Riverside').purpose('why: check field policy'))).rows
    assert rows[0]['display_name'] == 'Riverside'
    assert entries[-1].parameter_log_policies == ['masked', 'plain']
    assert entries[-1].masked_parameters == [True, False]
    await mutate(UpdateCommand('Customer', Value.I64(1)).expected_version(1).value('display_name', "O'Reilly"))
    await mutate(DeleteCommand('Customer', Value.I64(1)).expected_version(2))
    logs = '\n'.join(output)
    assert 'Ri*****de' in logs and "O''****ly" in logs
    assert 'Riverside' not in logs and "O''Reilly" not in logs
    assert 'LIMIT 1' in logs and '1 rows returned' in logs
    assert 'Parameterized SQL:' not in logs and 'REDACTED SQL' not in logs
    assert 'Riverside' not in repr(context.sql_logs())
    assert len(entries) == 4
