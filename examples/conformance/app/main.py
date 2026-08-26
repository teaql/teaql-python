import asyncio
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from E import E, TeaQLNotLoadedError
from Q import Q
from models.work_item import WorkItem
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.data_service import SQLiteTeaQLClient
from teaql.runtime import CheckException, UserContext


async def main() -> None:
    database = ROOT / ".local" / "conformance.sqlite"
    database.parent.mkdir(parents=True, exist_ok=True)
    database.unlink(missing_ok=True)
    client = SQLiteTeaQLClient(str(database))
    context = (UserContext.new().install(GENERATED_RUNTIME_MODULE)
               .insert_resource("dataService", client))

    await context.ensure_schema()
    print("PASS ensure_schema (explicit SQLite DDL)")

    invalid = WorkItem(platform=1)
    try:
        await invalid.audit_as("Checker must reject a missing title").save(context)
        raise AssertionError("Checker accepted a missing required title")
    except CheckException as error:
        assert any(result.rule_id == "required" and "title" in str(result.location)
                   for result in error.violations)
    rows_after_rejection = await (Q.work_items()
        .comment("Count work items after rejected mutation")
        .purpose("Verify Checker runs before provider SQL").execute_for_list(context))
    assert len(rows_after_rejection) == 0
    print("PASS Checker (canonical title key, rejected before persistence)")

    created = WorkItem(title="Verify Python runtime", platform=1)
    await created.audit_as("Create conformance work item").save(context)
    assert created.id is not None and created.version == 1
    print(f"PASS Create (id={created.id}, version={created.version})")

    queried = await (Q.work_items().with_id_is(created.id)
        .comment("Load the complete work item before mutation")
        .purpose("Verify typed Q API and update semantics").execute_for_one(context))
    assert isinstance(queried, WorkItem)
    assert queried.title == "Verify Python runtime"
    print("PASS Q API (typed WorkItem in SmartList boundary)")

    assert E.work_item(queried).title().eval() == "Verify Python runtime"
    assert E.work_item(queried).description().or_if_null("N/A") == "N/A"
    minimal = await (Q.work_items_minimal().with_id_is(created.id)
        .comment("Load only mandatory identity fields")
        .purpose("Verify E not-loaded semantics").execute_for_one(context))
    try:
        E.work_item(minimal).title().eval()
        raise AssertionError("E API treated not-loaded title as null")
    except TeaQLNotLoadedError:
        pass
    print("PASS E API (loaded, null fallback, and not-loaded are distinct)")

    previous_version = queried.version
    await queried.update_title("Verified Python runtime").audit_as("Update conformance work item").save(context)
    assert queried.version == previous_version + 1
    print(f"PASS Update (version {previous_version} -> {queried.version})")

    await queried.mark_as_deleted().audit_as("Delete conformance work item").save(context)
    remaining = await (Q.work_items().with_id_is(created.id)
        .comment("Verify soft-deleted work item is excluded")
        .purpose("Verify delete semantics").execute_for_list(context))
    assert len(remaining) == 0
    print("PASS Delete (default Q excludes deleted rows)")
    await client.close()
    print("PASS Python minimum runtime conformance: 7/7")


if __name__ == "__main__":
    asyncio.run(main())
