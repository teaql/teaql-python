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

    query_cases = [
        ("string equality", Q.schools().with_name_is("Riverside Primary School"), 1),
        ("string inequality", Q.schools().with_name_is_not("Another School"), 1),
        ("string membership", Q.schools().with_name_in("Riverside Primary School", "Another School"), 1),
        ("negative membership", Q.schools().with_name_not_in("Another School"), 1),
        ("contains", Q.schools().with_name_containing("Primary"), 1),
        ("negative contains", Q.schools().with_name_not_containing("Secondary"), 1),
        ("starts with", Q.schools().with_name_starting_with("Riverside"), 1),
        ("negative starts with", Q.schools().with_name_not_starting_with("Lakeside"), 1),
        ("ends with", Q.schools().with_name_ending_with("School"), 1),
        ("negative ends with", Q.schools().with_name_not_ending_with("Academy"), 1),
        ("number range", Q.schools().with_student_capacity_between(700, 900), 1),
        ("strict comparison", Q.schools().with_student_capacity_greater_than(799).with_student_capacity_less_than(801), 1),
        ("date range", Q.schools().with_established_date_between(date(1995, 1, 1), date(1995, 12, 31)), 1),
        ("known", Q.schools().with_address_is_known(), 1),
        ("unknown", Q.schools().with_address_is_unknown(), 0),
        ("boolean true", Q.schools().which_are_active(), 1),
        ("boolean false", Q.schools().which_are_not_active(), 0),
        ("constant relation", Q.schools().with_school_type_is_primary(), 1),
    ]
    for label, request, expected in query_cases:
        result = await (request.comment(f"Query parity: {label}")
            .purpose("Execute the shared School Query conformance case")
            .execute_for_list(context))
        assert len(result) == expected, f"{label}: expected {expected}, got {len(result)}"

    projected = await (Q.schools().select_name().order_by_id_descending()
        .comment("Query parity: projection and ordering")
        .purpose("Execute the shared School Query conformance case")
        .execute_for_list(context))
    assert len(projected) == 1 and projected[0].name == "Riverside Primary School"
    print("PASS Python School Management: bootstrap, portable Query parity, and forward relations")
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
