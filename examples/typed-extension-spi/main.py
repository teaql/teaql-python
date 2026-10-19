"""Small, complete demonstration of six typed Context extension contracts."""

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

import aiosqlite

from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.mutation import InsertCommand, MutationRequest
from teaql.core.query import SelectQuery
from teaql.core.value import DataType
from teaql.data_service import QueryRequest
from teaql.provider.sqlite import SimpleSchemaProvider, create_sqlite_service
from teaql.runtime import RuntimeModule


class SchoolPolicy:
    def __init__(self):
        self.deny = False
        self.calls = 0

    def apply(self, query):
        self.calls += 1
        if self.deny:
            raise PermissionError("school query denied")


class SchoolChecker:
    def check_and_fix(self, context, record, location, results):
        if not record.get("name") or not record["name"].val:
            raise ValueError("school name required")


class SchoolCheckerRegistry:
    def checker(self, entity):
        return SchoolChecker() if entity == "School" else None


class SchemaOnly:
    def __init__(self, service):
        self.service = service
        self.calls = 0

    async def _ensure_schema(self, context, capability):
        self.calls += 1
        await self.service._ensure_schema(context, capability)


class AuditSink:
    def __init__(self):
        self.events = []

    def on_safe_event(self, context, event):
        self.events.append(event)


class Telemetry:
    def __init__(self):
        self.operations = []

    def start(self, operation):
        self.operations.append(operation.name)

        class Scope:
            def success(self, attributes=None): pass
            def failure(self, error): pass

        return Scope()


class InternalIds:
    def __init__(self):
        self.level = 699
        self.lock = asyncio.Lock()

    async def next_id(self, entity):
        async with self.lock:
            self.level += 1
            return self.level

    async def ensure_id_floor(self, entity, floor):
        async with self.lock:
            self.level = max(self.level, floor)


async def run():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "typed-spi.db"
        school = (EntityDescriptor("School").table_name("school_data")
                  .property(PropertyDescriptor("id", DataType.I64).is_id())
                  .property(PropertyDescriptor("version", DataType.I64).is_version())
                  .property(PropertyDescriptor("name", DataType.Text)))
        provider = SimpleSchemaProvider()
        provider.register_entity(school)
        service = create_sqlite_service(str(path), provider)
        policy, audit, telemetry = SchoolPolicy(), AuditSink(), Telemetry()
        schema, ids = SchemaOnly(service), InternalIds()
        context = (RuntimeModule.new().entity(school).into_context()
                   .insert_resource("dataService", service)
                   .with_schema_provider(schema)
                   .with_request_policy(policy)
                   .with_checker_registry(SchoolCheckerRegistry())
                   .with_app_audit_event_sink(audit)
                   .with_runtime_telemetry(telemetry)
                   .with_internal_id_allocator(ids))
        context.disable_sql_log()
        assert not hasattr(schema, "query") and not hasattr(schema, "mutate")
        await context.ensure_schema()
        await context.ensure_schema()
        assert schema.calls == 2

        await service.mutate(context, MutationRequest(
            InsertCommand.new("School").value("name", "Riverside"),
            comment="create reviewed school"))
        request = QueryRequest(SelectQuery("School").project("id", "name"),
                               _comment="load schools", _purpose="verify accepted school")
        rows = (await service.query(context, context.prepare_query_request(request))).rows
        assert [(row["id"], row["name"]) for row in rows] == [(700, "Riverside")]
        assert policy.calls == 1 and len(audit.events) == 1
        assert telemetry.operations

        policy.deny = True
        try:
            context.prepare_query_request(request)
        except PermissionError:
            pass
        else:
            raise AssertionError("denied policy must block query preparation")
        try:
            await service.mutate(context, MutationRequest(
                InsertCommand.new("School").value("name", ""),
                comment="reject nameless school"))
        except ValueError:
            pass
        else:
            raise AssertionError("checker must reject invalid school")
        async with aiosqlite.connect(path) as db:
            async with db.execute("SELECT id FROM school_data") as cursor:
                assert [row[0] for row in await cursor.fetchall()] == [700]
        await service.close()
    print("PASS Python typed Context extension SPI example")


if __name__ == "__main__":
    asyncio.run(run())
