"""#236: actual SQLite boundary writes and authoritative signed-64 readback."""
import sqlite3

import pytest

from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.mutation import DeleteCommand, InsertCommand, MutationRequest, RecoverCommand, UpdateCommand
from teaql.core.value import DataType
from teaql.provider.sqlite import SimpleSchemaProvider, create_sqlite_service
from teaql.runtime import RuntimeModule


MAX = (1 << 63) - 1
MIN = -(1 << 63)


@pytest.mark.asyncio
@pytest.mark.parametrize("operation,original,expected", [
    ("update", MAX - 1, MAX), ("delete", MAX, MIN), ("recover", MIN + 2, MAX),
])
async def test_real_sqlite_legal_endpoints_readback_and_rejected_retry(tmp_path, operation, original, expected):
    database = tmp_path / "boundaries.sqlite"
    descriptor = (EntityDescriptor("VersionProbe").table_name("version_probe")
        .property(PropertyDescriptor("id", DataType.I64).is_id())
        .property(PropertyDescriptor("version", DataType.I64).is_version())
        .property(PropertyDescriptor("name", DataType.Text)))
    schema = SimpleSchemaProvider()
    schema.register_entity(descriptor)
    service = create_sqlite_service(str(database), schema)
    context = RuntimeModule().schema_entity(descriptor).into_context().with_schema_provider(service)
    try:
        await context.ensure_schema()
        await service.mutate(context, MutationRequest.Insert(InsertCommand.new("VersionProbe")
            .value("id", 7).value("name", "before"), "create native version fixture"))
        # Deliberate boundary injection only; ordinary mutations below use TeaQL.
        with sqlite3.connect(database) as connection:
            connection.execute("UPDATE version_probe SET version=? WHERE id=7", [original])
        if operation == "update":
            command = UpdateCommand.new("VersionProbe", 7).expected_version(original).value("name", "last legal")
        elif operation == "delete":
            command = DeleteCommand.new("VersionProbe", 7).expected_version(original)
        else:
            command = RecoverCommand.new("VersionProbe", 7, original)
        result = await service.mutate(context, MutationRequest(command, "execute last legal transition"))
        assert result.affected_rows == 1 and result.persisted_record["version"] == expected
        with sqlite3.connect(database) as connection:
            before = connection.execute("SELECT id,version,name FROM version_probe").fetchall()
        calls = []
        async def forbidden(*args):
            calls.append("provider")
            raise AssertionError("invalid version reached provider")
        begin, execute, fetch = service.transport.begin_sql, service.transport.execute_sql, service.transport.fetch_all_sql
        service.transport.begin_sql = service.transport.execute_sql = service.transport.fetch_all_sql = forbidden
        bad = (RecoverCommand.new("VersionProbe", 7, expected) if operation == "delete" else
               UpdateCommand.new("VersionProbe", 7).expected_version(expected).value("name", "pending"))
        with pytest.raises(ValueError):
            await service.mutate(context, MutationRequest(bad, "reject exhausted version without I/O"))
        assert calls == []
        with sqlite3.connect(database) as connection:
            assert connection.execute("SELECT id,version,name FROM version_probe").fetchall() == before
        service.transport.begin_sql, service.transport.execute_sql, service.transport.fetch_all_sql = begin, execute, fetch
        if operation == "delete":
            blind = await service.mutate(context, MutationRequest.Delete(DeleteCommand.new("VersionProbe", 7), "blind deletion is live only"))
            assert blind.affected_rows == 0
            with sqlite3.connect(database) as connection:
                assert connection.execute("SELECT id,version,name FROM version_probe").fetchall() == before
            hard = await service.mutate(context, MutationRequest.Delete(DeleteCommand.new("VersionProbe", 7)
                .expected_version(MIN).hard_delete(), "explicit physical tombstone removal"))
            assert hard.affected_rows == 1
    finally:
        await service.close()
