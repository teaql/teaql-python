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
    await client.ensure_schema()

    platform = Q.platforms().comment("Create the example root").purpose(
        "Prepare the School example").new_entity(context)
    platform.update_name("Campus Learning Platform")
    platform.update_base_url("https://campus.example.com")
    await platform.audit_as("Seed the School example root").save(context)
    primary = Q.school_types().comment("Create the primary school type").purpose(
        "Prepare the School example").new_entity(context)
    primary.update_platform(Platform.refer(platform.id))
    primary.update_name("Primary")
    primary.update_code("PRIMARY")
    primary.update_display_order(1)
    await primary.audit_as("Seed the primary school constant").save(context)

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
    print("PASS Python School Management: multi-word hydration and forward relations")
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
