"""Generated Q/E and checked graph saves, twice on one retained SQLite file."""
import asyncio
import json
import os
import pathlib
import sys
import tempfile

EXAMPLE = pathlib.Path(__file__).resolve().parents[1]
REPO = EXAMPLE.parents[1]
sys.path[:0] = [str(EXAMPLE), str(REPO / "src")]
database = pathlib.Path(os.environ["TEAQL_MANAGED_CREATION_DB"]) if "TEAQL_MANAGED_CREATION_DB" in os.environ else pathlib.Path(tempfile.mkdtemp(prefix="teaql-python-managed-evidence-")) / "managed.sqlite"
print("Retained managed creation database: " + str(database))
from Q import Q
from E import E
from models.work_item import WorkItem
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.data_service import SQLiteTeaQLClient
from teaql.core.entity_creation import EntityCreationError, EntityCreationState
from teaql.runtime import CheckException
from teaql.runtime.loaded_scalar_snapshot import LoadedScalarSnapshots


class Allocator:
    def __init__(self, provider):
        self.provider, self.calls = provider, []

    async def next_id(self, entity):
        self.calls.append(entity)
        return await self.provider.next_id(entity)

    async def ensure_id_floor(self, entity, floor):
        await self.provider.ensure_id_floor(entity, floor)


def items(identity=None):
    request = Q.work_items().limit(100)
    if identity is not None:
        request.with_id_is(identity)
    return request.comment("Inspect managed work items").purpose("Verify persisted creation state")


def platforms():
    return Q.platforms().with_id_is(1).limit(1).comment("Load the complete seeded platform").purpose("Verify graph mutation")


async def new_item(context):
    return (await items().new_entity(context)).update_platform(1)


async def flow(context, allocator, provider, round_number):
    await context.ensure_schema()
    await context.ensure_schema()
    root = await platforms().execute_for_one(context)
    assert root.id == 1
    assert LoadedScalarSnapshots.origin(root) is EntityCreationState.HYDRATED
    initial = await items().execute_for_list(context)

    invalid = await new_item(context)
    invalid.update_description("must not be inserted")
    try:
        await invalid.audit_as("Reject missing title before persistence").save(context)
    except CheckException as error:
        assert any(v.rule_id == "required" and "title" in str(v.location) for v in error.violations)
    else:
        raise AssertionError("Checker accepted missing title")
    assert len(await items().execute_for_list(context)) == len(initial)

    created = (await new_item(context)).update_title(f"managed item {round_number}")
    reserved_id, calls = created.id, list(allocator.calls)
    await created.audit_as("Persist the already reserved identity").save(context)
    assert created.id == reserved_id and created.version == 1
    assert allocator.calls == calls
    assert LoadedScalarSnapshots.origin(created) is EntityCreationState.HYDRATED
    loaded = await items(created.id).execute_for_one(context)
    assert E.work_item(loaded).title().eval() == f"managed item {round_number}"

    partial = await (Q.work_items_minimal().with_id_is(created.id).limit(1)
        .comment("Load only mandatory identity fields").purpose("Verify unchanged partial child admission")
        .execute_for_one(context))
    root.work_item_list().append(partial)
    root.update_name(f"partial child unchanged {round_number}")
    calls = list(allocator.calls)
    await root.audit_as("Update only the fully loaded parent").save(context)
    assert allocator.calls == calls
    untouched = await items(created.id).execute_for_one(context)
    assert untouched.version == 1 and untouched.title == f"managed item {round_number}"

    partial.update_title("reject a changed partial child")
    try:
        await root.audit_as("Reject changes on an incomplete child").save(context)
    except CheckException as error:
        assert any(v.rule_id == "invalid_type" and "fully loaded" in v.message for v in error.violations)
    else:
        raise AssertionError("Changed partial child was saved")
    unchanged = await items(created.id).execute_for_one(context)
    assert unchanged.version == 1

    versionless = WorkItem.from_json(json.dumps({"id": str(created.id), "title": "snapshot without version", "description": None, "platform": "1"}))
    versionless.update_title("must reject before callbacks")
    original_execute = context.execute_graph_save
    def unexpected_execution(*args, **kwargs):
        raise AssertionError("Versionless snapshot reached graph execution")
    context.execute_graph_save = unexpected_execution
    try:
        await versionless.audit_as("Reject a versionless read snapshot").save(context)
    except EntityCreationError as error:
        assert error.code == "ENTITY_CREATION_CONTEXT_REQUIRED"
    else:
        raise AssertionError("Versionless hydrated mutation was accepted")
    finally:
        context.execute_graph_save = original_execute

    # An ordinary updater cannot manufacture a persisted-version baseline.
    versionless.update_version(1)
    context.execute_graph_save = unexpected_execution
    try:
        await versionless.audit_as("Reject a version filled after hydration").save(context)
    except EntityCreationError as error:
        assert error.code == "ENTITY_CREATION_CONTEXT_REQUIRED"
    else:
        raise AssertionError("Versionless snapshot manufactured a persisted version")
    finally:
        context.execute_graph_save = original_execute

    # Force a child provider failure after the parent mutation. The complete
    # transaction must roll back while the child keeps its reserved identity.
    root = await platforms().execute_for_one(context)
    original_name, original_version = root.name, root.version
    child = (await new_item(context)).update_title(f"rollback child {round_number}")
    child_id = child.id
    root.work_item_list().append(child)
    root.update_name(f"rollback parent {round_number}")
    begin, failure, observed = provider.begin, RuntimeError("controlled child write failure"), []
    async def controlled_begin(ctx):
        transaction = await begin(ctx)
        mutate = transaction.mutate
        async def reject_child(current, request):
            observed.append(request._data.entity)
            if request._data.entity == "WorkItem":
                raise failure
            return await mutate(current, request)
        transaction.mutate = reject_child
        return transaction
    provider.begin = controlled_begin
    try:
        await root.audit_as("Rollback a composed graph").save(context)
    except RuntimeError as error:
        assert error is failure
    else:
        raise AssertionError("Controlled child mutation unexpectedly succeeded")
    finally:
        provider.begin = begin
    assert observed == ["Platform", "WorkItem"]
    stored_root = await platforms().execute_for_one(context)
    assert (stored_root.name, stored_root.version) == (original_name, original_version)
    assert await items(child_id).execute_for_one(context) is None
    assert child.id == child_id and child._action == "Create"
    assert LoadedScalarSnapshots.origin(child) is EntityCreationState.RESERVED
    calls = list(allocator.calls)
    await root.audit_as("Retry the same reserved graph after rollback").save(context)
    assert allocator.calls == calls
    persisted_child = await items(child_id).execute_for_one(context)
    assert persisted_child.id == child_id and persisted_child.version == 1
    return {"round": round_number, "createdId": reserved_id, "retriedChildId": child_id,
        "checks": ["repeat-schema", "checker-before-sql", "reserved-save-once", "typed-q-e",
                   "unchanged-partial-child", "changed-partial-rejected", "versionless-before-callbacks", "graph-rollback-and-retry"]}


async def main():
    provider = SQLiteTeaQLClient(str(database))
    allocator = Allocator(provider)
    context = GENERATED_RUNTIME_MODULE.into_context().insert_resource("dataService", provider).with_internal_id_allocator(allocator)
    try:
        rounds = [await flow(context, allocator, provider, number) for number in (1, 2)]
        print("PYTHON_MANAGED_SQLITE=" + json.dumps({"rounds": rounds}, sort_keys=True))
    finally:
        await provider.close()


if __name__ == "__main__":
    asyncio.run(main())
