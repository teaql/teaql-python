import os
from datetime import date

import pytest

from teaql.provider.mysql.transport import MysqlTransport
from teaql.provider.postgres.transport import PostgresTransport
from teaql.sql.types import CompiledQuery
from teaql.sql.types import DatabaseKind
from teaql.core.value import Timestamp, Value


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("env_name", "transport_type", "sql"),
    [
        ("TEAQL_TEST_POSTGRES_URL", PostgresTransport,
         "SELECT id FROM (VALUES (1), (2), (3), (4), (5)) AS fixture(id) ORDER BY id"),
        ("TEAQL_TEST_MYSQL_URL", MysqlTransport,
         "SELECT id FROM (SELECT 1 id UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5) fixture ORDER BY id"),
    ],
)
async def test_stream_sql_against_real_database(env_name, transport_type, sql):
    url = os.getenv(env_name)
    if not url:
        pytest.skip(f"{env_name} is not set")
    chunks = [chunk async for chunk in transport_type(url).stream_sql(CompiledQuery(sql, []), 2)]
    assert [len(chunk) for chunk in chunks] == [2, 2, 1]
    assert [row["id"] for chunk in chunks for row in chunk] == [1, 2, 3, 4, 5]

@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("env_name", "transport_type", "dialect", "ddl", "sql"),
    [
        ("TEAQL_TEST_POSTGRES_URL", PostgresTransport, DatabaseKind.PostgreSql,
         "CREATE TABLE teaql_temporal_runtime_fixture(id INTEGER, d DATE, t TIMESTAMPTZ(3))",
         "INSERT INTO teaql_temporal_runtime_fixture VALUES ($1, $2, $3)"),
        ("TEAQL_TEST_MYSQL_URL", MysqlTransport, DatabaseKind.MySql,
         "CREATE TABLE teaql_temporal_runtime_fixture(id INTEGER, d DATE, t DATETIME(3))",
         "INSERT INTO teaql_temporal_runtime_fixture VALUES (%s, %s, %s)"),
    ],
)
async def test_temporal_debug_sql_against_real_database(env_name, transport_type, dialect, ddl, sql):
    url = os.getenv(env_name)
    if not url:
        pytest.skip(f"{env_name} is not set")
    transport = transport_type(url)
    await transport.execute_sql(CompiledQuery("DROP TABLE IF EXISTS teaql_temporal_runtime_fixture", []))
    await transport.execute_sql(CompiledQuery(ddl, []))
    prepared = CompiledQuery(sql, [
        Value.I64(1), Value.Date(date(2024, 2, 29)), Value.Timestamp(Timestamp(-315521754322))
    ], "teaql source=temporal.verify ? $1")
    await transport.execute_sql(prepared)
    literal = prepared.debug_sql(dialect).replace("VALUES (1,", "VALUES (2,", 1)
    await transport.execute_sql(CompiledQuery(literal, []))
    rows = await transport.fetch_all_sql(CompiledQuery(
        "SELECT d, t FROM teaql_temporal_runtime_fixture ORDER BY id", []))
    assert rows[0] == rows[1]
    await transport.execute_sql(CompiledQuery("DROP TABLE teaql_temporal_runtime_fixture", []))
