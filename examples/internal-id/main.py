"""Run a small end-to-end Internal ID capability example."""

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

import aiosqlite

from teaql.core.entity import EntityKey
from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.mutation import InsertCommand, MutationRequest
from teaql.core.value import DataType
from teaql.provider.sqlite import SimpleSchemaProvider, create_sqlite_service
from teaql.runtime import RuntimeModule


class ExampleAllocator:
    def __init__(self):
        self._level = 99
        self._lock = asyncio.Lock()

    async def next_id(self, entity: str) -> int:
        assert entity == "School"
        async with self._lock:
            self._level += 1
            return self._level

    async def ensure_id_floor(self, entity: str, floor: int) -> None:
        assert entity == "School"
        async with self._lock:
            self._level = max(self._level, floor)


def school_insert(name: str, identity: int | None = None) -> MutationRequest:
    command = InsertCommand.new("School").value("name", name)
    if identity is not None:
        command.value("id", identity)
    return MutationRequest(command, comment="create school with custom internal ID")


async def run() -> None:
    with TemporaryDirectory() as directory:
        path = Path(directory) / "internal-id.db"
        school = (EntityDescriptor("School").table_name("school_data")
                  .property(PropertyDescriptor("id", DataType.I64).is_id())
                  .property(PropertyDescriptor("version", DataType.I64).is_version())
                  .property(PropertyDescriptor("name", DataType.Text)))
        provider = SimpleSchemaProvider()
        provider.register_entity(school)
        service = create_sqlite_service(str(path), provider)
        context = (RuntimeModule.new().entity(school).into_context()
                   .with_schema_provider(service)
                   .insert_resource("dataService", service)
                   .with_internal_id_allocator(ExampleAllocator()))
        context.disable_sql_log()
        await context.ensure_schema()

        await service.mutate(context, school_insert("Direct"))
        await service.mutate(context, MutationRequest.Batch([
            school_insert("Batch"),
            MutationRequest.Batch([school_insert("Nested")], comment="nested schools"),
        ], comment="batch schools"))
        await service.mutate(context, school_insert("Explicit", 500))

        async def save_graph(graph):
            scope = graph.scope(EntityKey("School", 501))
            return await graph.transaction.mutate(
                graph.context,
                graph.request(InsertCommand.new("School").value("name", "Graph"), scope),
            )

        await context.execute_graph_save(save_graph, comment="save school graph")
        async with aiosqlite.connect(path) as db:
            async with db.execute("SELECT id FROM school_data ORDER BY id") as rows:
                assert [row[0] for row in await rows.fetchall()] == [100, 101, 102, 500, 501]
            async with db.execute("SELECT COUNT(*) FROM teaql_id_space") as rows:
                assert (await rows.fetchone())[0] == 0
        await service.close()
    print("PASS Python context-owned Internal ID example")


if __name__ == "__main__":
    asyncio.run(run())
