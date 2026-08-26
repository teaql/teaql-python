import asyncio
from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Q import Q
from models.platform import Platform
from models.school_type import SchoolType
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.data_service import SQLiteTeaQLClient
from teaql.runtime import UserContext


async def main() -> None:
    database = ROOT / ".local" / "school.sqlite"
    database.parent.mkdir(parents=True, exist_ok=True)
    database.unlink(missing_ok=True)
    client = SQLiteTeaQLClient(str(database))
    context = (UserContext.new().install(GENERATED_RUNTIME_MODULE)
               .insert_resource("dataService", client))
    await context.ensure_schema()
    await context.ensure_schema()
    platform = await (Q.platforms().with_id_is(1)
        .comment("Load the generated domain root")
        .purpose("Verify idempotent schema bootstrap").execute_for_one(context))
    primary = await (Q.school_types().with_id_is(1001)
        .comment("Load the generated Primary constant")
        .purpose("Verify idempotent schema bootstrap").execute_for_one(context))
    constants = await (Q.school_types().comment("Load generated constants")
        .purpose("Verify idempotent schema bootstrap").execute_for_list(context))
    assert platform.id == 1
    assert [(item.id, item.code) for item in constants] == [
        (1001, "PRIMARY"), (1002, "SECONDARY")]
    assert [item.version for item in constants] == [1, 1]

    GENERATED_RUNTIME_MODULE.initial_graphs[0].set("name", "Primary School")
    await context.ensure_schema()
    reconciled = await (Q.school_types().with_id_is(1001)
        .comment("Load the reconciled Primary constant")
        .purpose("Verify model-defined constant updates").execute_for_one(context))
    assert reconciled.name == "Primary School"
    assert reconciled.version == 2

    school = Q.schools().comment("Create the example school").purpose(
        "Verify generated Python mutations").new_entity(context)
    school.update_platform(Platform.refer(platform.id))
    school.update_school_type(SchoolType.refer(primary.id))
    school.update_name("Riverside Primary School")
    school.update_address("12 River Road, Springfield")
    school.update_established_date(date(1995, 9, 1))
    school.update_student_capacity(800)
    school.update_active(True)
    await school.audit_as("Create Riverside Primary School").save(context)

    loaded = await (Q.schools().with_id_is(school.id)
        .select_platform_with(Q.platforms_minimal().select_name().select_base_url())
        .select_school_type_with(Q.school_types_minimal().select_name().select_code().select_display_order())
        .comment("Load a school with its forward relations")
        .purpose("Verify column mapping and relation hydration")
        .execute_for_one(context))
    assert loaded.name == "Riverside Primary School"
    assert str(loaded.establishedDate).startswith("1995-09-01")
    assert loaded.studentCapacity == 800
    assert loaded.platform.name == "Campus Learning Platform"
    assert loaded.platform.baseUrl == "https://campus.example.com"
    assert loaded.schoolType.code == "PRIMARY"
    assert loaded.schoolType.displayOrder == 1
    print("PASS Python School Management: idempotent bootstrap, multi-word hydration, and forward relations")
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
