"""Context-owned Internal ID allocation must reach every SQLite write path."""

import asyncio

import aiosqlite
import pytest

from teaql.core.entity import EntityKey
from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.mutation import InsertCommand, MutationRequest
from teaql.core.value import DataType
from teaql.provider.sqlite import SimpleSchemaProvider, create_sqlite_service
from teaql.runtime import InternalIdAllocator, RuntimeModule
from teaql.sql.executor import SqlDataServiceExecutor


class RecordingAllocator:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._levels = {}
        self.floors = []
        self.fail_next = False
        self.fail_floor = False

    async def next_id(self, entity: str) -> int:
        async with self._lock:
            if self.fail_next:
                raise RuntimeError("custom allocation rejected")
            next_value = self._levels.get(entity, 499) + 1
            self._levels[entity] = next_value
            return next_value

    async def ensure_id_floor(self, entity: str, floor: int) -> None:
        async with self._lock:
            if self.fail_floor:
                raise RuntimeError("custom floor rejected")
            self.floors.append((entity, floor))
            self._levels[entity] = max(self._levels.get(entity, 499), floor)


async def fixture(path, allocator=None):
    school = (EntityDescriptor("School").table_name("school_data")
              .property(PropertyDescriptor("id", DataType.I64).is_id())
              .property(PropertyDescriptor("version", DataType.I64).is_version())
              .property(PropertyDescriptor("name", DataType.Text)))
    provider = SimpleSchemaProvider()
    provider.register_entity(school)
    service = create_sqlite_service(str(path), provider)
    context = RuntimeModule.new().entity(school).into_context()
    context.with_schema_provider(service).insert_resource("dataService", service)
    context.disable_sql_log()
    if allocator is not None:
        context.with_internal_id_allocator(allocator)
    await context.ensure_schema()
    return service, context


def insert(name, identity=None):
    command = InsertCommand.new("School").value("name", name)
    if identity is not None:
        command.value("id", identity)
    return MutationRequest(command, comment="save school with internal ID allocator")


async def ids(path):
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT id FROM school_data ORDER BY id") as cursor:
            return [row[0] for row in await cursor.fetchall()]


async def assert_no_default_id_space_rows(path):
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT COUNT(*) FROM teaql_id_space") as cursor:
            assert (await cursor.fetchone())[0] == 0


@pytest.mark.asyncio
async def test_context_allocator_reaches_direct_nested_batch_explicit_and_graph(tmp_path, monkeypatch):
    async def forbidden_provider_id(*args, **kwargs):
        raise AssertionError("default provider ID space must not be called")

    monkeypatch.setattr(SqlDataServiceExecutor, "next_id", forbidden_provider_id)
    monkeypatch.setattr(SqlDataServiceExecutor, "ensure_id_floor", forbidden_provider_id)
    path = tmp_path / "school.db"
    allocator = RecordingAllocator()
    assert isinstance(allocator, InternalIdAllocator)
    service, context = await fixture(path, allocator)
    await service.mutate(context, insert("direct"))
    await service.mutate(context, MutationRequest.Batch([
        insert("batch one"),
        MutationRequest.Batch([insert("batch nested")], comment="nested batch"),
    ], comment="batch of schools"))
    await service.mutate(context, insert("explicit", 900))

    async def graph_save(graph):
        scope = graph.scope(EntityKey("School", 901))
        return await graph.transaction.mutate(graph.context,
            graph.request(InsertCommand.new("School").value("name", "graph"), scope))

    await context.execute_graph_save(graph_save, comment="save school graph")
    assert await ids(path) == [500, 501, 502, 900, 901]
    assert ("School", 900) in allocator.floors
    await assert_no_default_id_space_rows(path)
    await service.close()


@pytest.mark.asyncio
async def test_allocator_concurrent_allocations_are_unique_per_entity():
    allocator = RecordingAllocator()
    ids = await asyncio.gather(*(allocator.next_id("School") for _ in range(24)))
    assert sorted(ids) == list(range(500, 524))
    assert await allocator.next_id("Vendor") == 500


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["next", "floor"])
async def test_custom_failure_does_not_fall_back_or_write(tmp_path, failure, monkeypatch):
    async def forbidden_provider_id(*args, **kwargs):
        raise AssertionError("default provider ID space must not be called")

    monkeypatch.setattr(SqlDataServiceExecutor, "next_id", forbidden_provider_id)
    monkeypatch.setattr(SqlDataServiceExecutor, "ensure_id_floor", forbidden_provider_id)
    path = tmp_path / "failure.db"
    allocator = RecordingAllocator()
    service, context = await fixture(path, allocator)
    allocator.fail_next = failure == "next"
    allocator.fail_floor = failure == "floor"
    request = insert("rejected", 900 if failure == "floor" else None)
    with pytest.raises(RuntimeError, match="custom (allocation|floor) rejected"):
        await service.mutate(context, request)
    assert await ids(path) == []
    await assert_no_default_id_space_rows(path)
    await service.close()


@pytest.mark.asyncio
async def test_without_override_retains_provider_id_space(tmp_path):
    path = tmp_path / "default.db"
    service, context = await fixture(path)
    await service.mutate(context, insert("default"))
    assert await ids(path) == [1]
    await service.close()


def test_malformed_or_old_synchronous_generator_is_rejected_before_use():
    from teaql.runtime import UserContext
    class Incomplete:
        async def next_id(self, entity):
            return 5
    class Synchronous:
        def next_id(self, entity):
            return 5
        def ensure_id_floor(self, entity, floor):
            return None
    with pytest.raises(TypeError, match="next_id.*ensure_id_floor"):
        UserContext().with_internal_id_allocator(Incomplete())
    with pytest.raises(TypeError, match="must be async"):
        UserContext().with_internal_id_allocator(Synchronous())
    with pytest.raises(TypeError, match="next_id.*ensure_id_floor"):
        UserContext().with_internal_id_generator(object())
