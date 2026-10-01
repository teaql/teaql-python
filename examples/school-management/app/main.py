import asyncio
from datetime import date
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Q import Q
from E import E
from models.platform import Platform
from models.school_type import SchoolType
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.data_service import SQLiteTeaQLClient
from teaql.runtime import UserContext
from teaql.core.dynamic_search import normalize_dynamic_search
from teaql.core import RequestIntentError
from teaql.runtime.context import SqlLogOptions


async def verify_request_intent(context, client):
    calls = []
    context.with_sql_log_options(SqlLogOptions.disabled())
    context.with_request_policy(lambda _: calls.append('policy'))
    original_allocator = client.next_id
    async def counted_allocator(entity):
        calls.append('id allocator')
        return await original_allocator(entity)
    client.next_id = counted_allocator
    try:
        executions = [
            (Q.schools().purpose('render schools').execute_for_list(context), 'REQUEST_COMMENT_REQUIRED'),
            (Q.schools().comment('load schools').purpose('\u0085').execute_for_rows(context), 'QUERY_PURPOSE_REQUIRED'),
            (Q.schools().purpose('render page').execute_for_page(context, 0, 10), 'REQUEST_COMMENT_REQUIRED'),
        ]
        for execution, code in executions:
            try:
                await execution
                raise AssertionError('missing generated request gate')
            except RequestIntentError as error:
                assert error.code == code
        try:
            async for _ in Q.schools().purpose('stream schools').execute_for_stream(context):
                raise AssertionError('stream must not open')
        except RequestIntentError as error:
            assert error.code == 'REQUEST_COMMENT_REQUIRED'
        entity = Q.schools().comment('prepare unsaved school').purpose('verify save gate').new_entity(context)
        for reason in (None, '\u0085'):
            try:
                if reason is not None:
                    entity.audit_as(reason)
                await entity.save(context)
                raise AssertionError('missing generated mutation gate')
            except RequestIntentError as error:
                assert error.code == 'REQUEST_COMMENT_REQUIRED'
        assert calls == [], calls
        assert entity.id is None
    finally:
        client.next_id = original_allocator
        context.clear_request_policy()
        context.with_sql_log_options(SqlLogOptions.all())
    assert len(await Q.schools().comment('verify rejected writes').purpose('check empty table').execute_for_list(context)) == 0
    print('PASS Python generated request intent: list/rows/page/stream/save reject before policy and ID allocation with logs off')


async def verify_dynamic_search(context):
    models = {
        "School": {"fields": {"name": "string"}, "relations": {"platform": "Platform"}},
        "Platform": {"fields": {"name": "string"}, "relations": {}},
    }
    populated = {"filter": {"name": "Riverside Primary School", "platform.name": "Deployment Campus",
        "removed": "SECRET_VALUE", "platform.removed": "SECRET_VALUE"},
        "orderBy": [{"field": "removed", "direction": "asc"}]}
    for authorized_platform in (1, 2):
        for search_input in (populated, {}):
            # Authorization remains present even when the entire search form is absent.
            request = Q.schools().with_name_is("Riverside Primary School").with_platform_matching(
                Q.platforms().with_id_is(authorized_platform))
            search, warnings = normalize_dynamic_search(search_input, "School", models, lambda _: None)
            for field, predicate in search["filter"].items():
                value = predicate.get("$eq")
                if not isinstance(value, str):
                    raise ValueError("Demo binding supports string equality only")
                if field == "name":
                    request = request.with_name_is(value)
                elif field == "platform.name":
                    request = request.with_platform_matching(Q.platforms().with_name_is(value))
                else:
                    raise ValueError("Missing trusted demo binding")
            rows = await (request.order_by_id_descending().limit(2)
                .comment("what: generated School dynamic search")
                .purpose("why: retain related authorization with stale or absent search fields")
                .execute_for_list(context))
            assert len(rows) == (1 if authorized_platform == 1 else 0)
            assert len(warnings) == (3 if search_input is populated else 0)
            assert "SECRET_VALUE" not in str(warnings)
    print("PASS Python generated School dynamic search: independent related scope and typed Q bindings")


async def main() -> None:
    database = Path(os.environ.get("TEAQL_SCHOOL_MANAGEMENT_DB", ROOT / ".local" / "school.sqlite"))
    database.parent.mkdir(parents=True, exist_ok=True)
    database.unlink(missing_ok=True)
    client = SQLiteTeaQLClient(str(database))
    context = (UserContext.new().install(GENERATED_RUNTIME_MODULE)
               .insert_resource("dataService", client))
    await context.ensure_schema()
    await context.ensure_schema()
    await verify_request_intent(context, client)
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
    first_primary_version = primary.version

    import aiosqlite
    connection = await aiosqlite.connect(database)
    cursor = await connection.execute(
        "SELECT current_level FROM teaql_id_space WHERE type_name = ?", ("SchoolType",))
    id_floor = await cursor.fetchone()
    await cursor.close()
    assert id_floor is not None and id_floor[0] >= 1002
    await connection.execute("UPDATE platform_data SET name = ? WHERE id = 1", ("Deployment Campus",))
    await connection.execute("UPDATE school_type_data SET name = ? WHERE id = 1001", ("Drifted Primary",))
    await connection.commit()
    await connection.close()
    await context.ensure_schema()
    preserved_root = await (Q.platforms().with_id_is(1)
        .comment("Load the deployment-owned root")
        .purpose("Verify generated bootstrap preserves an existing root").execute_for_one(context))
    reconciled = await (Q.school_types().with_id_is(1001)
        .comment("Load the reconciled Primary constant")
        .purpose("Verify model-defined constant updates").execute_for_one(context))
    assert preserved_root.name == "Deployment Campus"
    assert reconciled.name == "Primary"
    assert reconciled.version == first_primary_version + 1

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

    await verify_dynamic_search(context)

    loaded = await (Q.schools().with_id_is(school.id)
        .select_platform_with(Q.platforms_minimal().select_name().select_base_url())
        .select_school_type_with(Q.school_types_minimal().select_name().select_code().select_display_order())
        .comment("Load a school with its forward relations")
        .purpose("Verify column mapping and relation hydration")
        .execute_for_one(context))
    assert loaded.name == "Riverside Primary School"
    assert str(loaded.establishedDate).startswith("1995-09-01")
    assert loaded.studentCapacity == 800
    assert loaded.platform.name == "Deployment Campus"
    assert loaded.platform.baseUrl == "https://campus.example.com"
    assert loaded.schoolType.code == "PRIMARY"
    assert loaded.schoolType.displayOrder == 1
    assert E.school(loaded).school_type().code().eval() == 'PRIMARY'
    assert E.school(loaded).platform().name().eval() == 'Deployment Campus'

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
