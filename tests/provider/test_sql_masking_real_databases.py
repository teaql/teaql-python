"""Opt-in live PostgreSQL/MySQL masking contract for the SQL providers."""

import os
from types import SimpleNamespace
from uuid import uuid4

import pytest

from teaql.core.expr import Expr
from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.mutation import InsertCommand, MutationRequest, TraceNode
from teaql.core.query import SelectQuery
from teaql.core.value import DataType
from teaql.data_service import QueryRequest
from teaql.provider.mysql.dialect import MysqlDialect
from teaql.provider.mysql.transport import MysqlTransport
from teaql.provider.postgres.dialect import PostgresDialect
from teaql.provider.postgres.transport import PostgresTransport
from teaql.provider.sqlite import SimpleSchemaProvider
from teaql.runtime import RuntimeModule
from teaql.runtime.context import SqlLogOperation, TextDiagnosticSqlLogSink
from teaql.sql.executor import SqlDataServiceExecutor
from teaql.sql.types import CompiledQuery, DatabaseKind


def test_mysql_dialect_implements_sql_contract():
    dialect = MysqlDialect()
    assert dialect.kind() == DatabaseKind.MySql
    assert dialect.quote_ident("order") == "`order`"
    assert dialect.placeholder(1) == "%s"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("env_name", "dialect_type", "transport_type"),
    [
        ("TEAQL_TEST_POSTGRES_URL", PostgresDialect, PostgresTransport),
        ("TEAQL_TEST_MYSQL_URL", MysqlDialect, MysqlTransport),
    ],
)
async def test_live_provider_keeps_values_and_masks_q_and_mutation(
    env_name, dialect_type, transport_type
):
    url = os.getenv(env_name)
    if not url:
        if os.getenv("TEAQL_REQUIRE_LIVE_DB", "").lower() == "true":
            pytest.fail(f"{env_name} is required for live provider tests")
        pytest.skip(f"{env_name} is not set")

    table = f"teaql_mask_{uuid4().hex[:12]}"
    entity = (
        EntityDescriptor("Customer")
        .table_name(table)
        .property(PropertyDescriptor("id", DataType.I64).is_id())
        .property(PropertyDescriptor("version", DataType.I64).is_version())
        .property(PropertyDescriptor("display_name", DataType.Text))
        .property(PropertyDescriptor("public_address", DataType.Text).log_policy("plain"))
        .property(PropertyDescriptor("password_hash", DataType.Text))
        .audit_mask_fields(["display_name", "password_hash"])
    )
    provider = SimpleSchemaProvider()
    provider.register_entity(entity)
    transport = transport_type(url)
    service = SqlDataServiceExecutor(dialect_type(), transport, provider)
    context = RuntimeModule.new().entity(entity).into_context().with_schema_provider(service)
    lines = []
    entries = []
    sink = TextDiagnosticSqlLogSink(lines.append)

    def capture(entry):
        entries.append(entry)
        sink.write(entry)

    context.set_diagnostic_sql_log_sink(SimpleNamespace(write=capture))

    try:
        await context.ensure_schema()
        command = (
            InsertCommand("Customer")
            .value("id", 1)
            .value("version", 1)
            .value("display_name", "Riverside")
            .value("public_address", "1 Runtime Road")
            .value("password_hash", "PASSWORD-CANARY")
        )
        command.trace_chain = [TraceNode(comment="what: create masked customer")]
        await service.mutate(context, MutationRequest(command))
        query = SelectQuery("Customer").filter(
            Expr.new_and(
                Expr.eq("display_name", "Riverside"),
                Expr.eq("public_address", "1 Runtime Road"),
            )
        ).limit(1)
        rows = (
            await service.query(
                context,
                QueryRequest(query)
                .comment("what: read masked customer")
                .purpose("why: verify live-provider SQL masking"),
            )
        ).rows
        assert len(rows) == 1
        assert rows[0]["display_name"] == "Riverside"
        assert rows[0]["public_address"] == "1 Runtime Road"
        assert [entry.operation for entry in entries[-2:]] == [
            SqlLogOperation.Insert,
            SqlLogOperation.Select,
        ]
        assert entries[-1].parameter_log_policies == ["masked", "plain"]
        assert entries[-1].masked_parameters == [True, False]
        logged = "\n".join(lines)
        assert "Ri*****de" in logged
        assert "1 Runtime Road" in logged
        assert "what: read masked customer" in logged
        assert "why: verify live-provider SQL masking" in logged
        assert "SELECT" in logged
        assert "Riverside" not in logged
        assert "PASSWORD-CANARY" not in logged
    finally:
        await transport.execute_sql(CompiledQuery(f"DROP TABLE IF EXISTS {table}", []))
