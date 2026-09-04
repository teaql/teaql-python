import asyncio
from datetime import datetime, timezone
from teaql.runtime import CheckResult, ContextEntityRef, JsonFieldNamingProfile, ObjectLocation, RuntimeModule, create_wire_entity_metadata
from teaql.core.meta import EntityDescriptor, PropertyDescriptor, RelationDescriptor
from teaql.core.value import DataType
from Q import Q
from teaql.core.value import Value
try:
    from teaql.core.graph import GraphNode
except ImportError:
    class GraphNode:
        def __init__(self, entity):
            self.entity, self.fields = entity, {}
        def set(self, field, value):
            self.fields[field] = value
            return self
from models.platform import Platform
from models.work_item import WorkItem

def _teaql_is_null(value):
    return value.is_null() if hasattr(value, "is_null") else value is None

def _teaql_raw(value):
    return value.val if hasattr(value, "val") else value

def _teaql_entity_id(value):
    value = _teaql_raw(value)
    if hasattr(value, "id"):
        return value.id
    if isinstance(value, dict):
        return value.get("id")
    return value

class _PlatformChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        now = context.get_resource("fix_time")
        if (operation == "insert" and "name" not in record) or ("name" in record and _teaql_is_null(record["name"])):
            results.append(CheckResult("required", ObjectLocation().property("name")))
        if "name" in record and _teaql_raw(record["name"]) is not None and len(_teaql_raw(record["name"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("name"), _teaql_raw(record["name"]), 100))



class _WorkItemChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        now = context.get_resource("fix_time")
        if (operation == "insert" and "title" not in record) or ("title" in record and _teaql_is_null(record["title"])):
            results.append(CheckResult("required", ObjectLocation().property("title")))
        if "title" in record and _teaql_raw(record["title"]) is not None and not len(_teaql_raw(record["title"])) >= 1:
            results.append(CheckResult("min_length", ObjectLocation().property("title"), _teaql_raw(record["title"]), 1))
        if "title" in record and _teaql_raw(record["title"]) is not None and len(_teaql_raw(record["title"])) > 80:
            results.append(CheckResult("max_length", ObjectLocation().property("title"), _teaql_raw(record["title"]), 80))

        if "description" in record and _teaql_raw(record["description"]) is not None and len(_teaql_raw(record["description"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("description"), _teaql_raw(record["description"]), 100))

        if (operation == "insert" and "platform" not in record) or ("platform" in record and _teaql_is_null(record["platform"])):
            results.append(CheckResult("required", ObjectLocation().property("platform")))



_Platform_DESCRIPTOR = (EntityDescriptor("Platform")
    .table_name("platform_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").is_id().required()).property(PropertyDescriptor("name", DataType.Text).column_name("name").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").is_version().required()).relation(RelationDescriptor("work_item_list", "WorkItem").local("id").foreign("platform").many())
)

_WorkItem_DESCRIPTOR = (EntityDescriptor("WorkItem")
    .table_name("work_item_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").is_id().required()).property(PropertyDescriptor("title", DataType.Text).column_name("title").required()).property(PropertyDescriptor("description", DataType.Text).column_name("description")).property(PropertyDescriptor("platform", DataType.I64).column_name("platform").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").is_version().required()).relation(RelationDescriptor("platform", "Platform").local("platform").foreign("id"))
)

async def _ensure_generated_bootstrap_once(context):
    previous_actor = context.user_identifier() if hasattr(context, 'user_identifier') else None
    previous_category = context.get_resource('bootstrapCategory')
    if hasattr(context, 'set_user_identifier'):
        context.set_user_identifier('teaql-generated-bootstrap')
    context.insert_resource('bootstrapCategory', 'runtime-bootstrap')
    try:
        platform_1 = await (Q.platforms().with_id_is(1).comment('what: locate generated bootstrap entity').purpose('why: idempotent runtime bootstrap').execute_for_one(context))
        if platform_1 is None:
            platform_1 = Platform._teaql_new_with_fixed_id(1)
            platform_1.update_name("Runtime Example")
            try:
                await platform_1.audit_as('create model root Platform(1)').save(context)
            except Exception as _teaql_create_error:
                for _teaql_attempt in range(5):
                    platform_1 = await (Q.platforms().with_id_is(1).comment('what: recover concurrent bootstrap').purpose('why: make generated bootstrap idempotent').execute_for_one(context))
                    if platform_1 is not None:
                        break
                    if _teaql_attempt < 4:
                        await asyncio.sleep((_teaql_attempt + 1) * 0.01)
                if platform_1 is None:
                    raise _teaql_create_error
        context.with_active_root(ContextEntityRef("Platform", 1))
    finally:
        if hasattr(context, 'set_user_identifier'):
            context.set_user_identifier(previous_actor)
        context.insert_resource('bootstrapCategory', previous_category)

async def _ensure_generated_bootstrap(context):
    for _teaql_attempt in range(5):
        try:
            await _ensure_generated_bootstrap_once(context)
            return
        except Exception:
            if _teaql_attempt == 4:
                raise
            await asyncio.sleep((_teaql_attempt + 1) * 0.01)


# Passive generated manifest. Call ensure_schema() separately and explicitly.
GENERATED_RUNTIME_MODULE = (RuntimeModule().entity(Platform)
    .schema_entity(_Platform_DESCRIPTOR)
    .checker("Platform", _PlatformChecker())
    .wire_metadata("Platform", create_wire_entity_metadata("Platform", ["id", "name", "version"], JsonFieldNamingProfile.CAMEL_CASE, {"id": ["id"], "name": ["name"], "version": ["version"]})).entity(WorkItem)
    .schema_entity(_WorkItem_DESCRIPTOR)
    .checker("WorkItem", _WorkItemChecker())
    .wire_metadata("WorkItem", create_wire_entity_metadata("WorkItem", ["id", "title", "description", "platform", "version"], JsonFieldNamingProfile.CAMEL_CASE, {"id": ["id"], "title": ["title"], "description": ["description"], "platform": ["platform"], "version": ["version"]}))
    .generated_bootstrap(_ensure_generated_bootstrap)
)