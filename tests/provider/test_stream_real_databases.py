import os

import pytest

from teaql.provider.mysql.transport import MysqlTransport
from teaql.provider.postgres.transport import PostgresTransport
from teaql.sql.types import CompiledQuery


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
