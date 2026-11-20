"""SQLite-only durable replay store; all SQL runs on the owning transaction."""

from teaql.core.value import Value
from .types import CompiledQuery


SCHEMAS = ("""CREATE TABLE IF NOT EXISTS teaql_operation_results (
    scope TEXT NOT NULL,
    operation TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    result TEXT NOT NULL,
    PRIMARY KEY (scope, operation, idempotency_key)
)""", """CREATE TABLE IF NOT EXISTS teaql_operation_audit (
    scope TEXT NOT NULL,
    operation TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    actor TEXT NOT NULL,
    PRIMARY KEY (scope, operation, idempotency_key)
)""")


async def lookup(transport, scope, operation, key):
    rows = await transport.fetch_all_sql(CompiledQuery(
        "SELECT fingerprint, result FROM teaql_operation_results "
        "WHERE scope = ? AND operation = ? AND idempotency_key = ?",
        [Value.from_any(value) for value in (scope, operation, key)],
    ))
    return rows[0] if rows else None


async def store(transport, scope, operation, key, fingerprint, result, actor):
    await transport.execute_sql(CompiledQuery(
        "INSERT INTO teaql_operation_results "
        "(scope, operation, idempotency_key, fingerprint, result) VALUES (?, ?, ?, ?, ?)",
        [Value.from_any(value) for value in (scope, operation, key, fingerprint, result)],
    ))
    await transport.execute_sql(CompiledQuery(
        "INSERT INTO teaql_operation_audit "
        "(scope, operation, idempotency_key, fingerprint, actor) VALUES (?, ?, ?, ?, ?)",
        [Value.from_any(value) for value in (scope, operation, key, fingerprint, actor)],
    ))
