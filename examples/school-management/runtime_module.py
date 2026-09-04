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
from models.school_type import SchoolType
from models.school import School

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
        if operation == "insert" and ("create_time" not in record or _teaql_is_null(record["create_time"])):
            record["create_time"] = Value.from_any(now)
            context.record_fix_evidence("Platform", "create_time", "clock", "graphClock")

        if operation == "insert" and ("update_time" not in record or _teaql_is_null(record["update_time"])):
            record["update_time"] = Value.from_any(now)
            context.record_fix_evidence("Platform", "update_time", "clock", "graphClock")
        if operation == "insert" or operation == "update":
            record["update_time"] = Value.from_any(now)
            context.record_fix_evidence("Platform", "update_time", "clock", "graphClock")


        if (operation == "insert" and "name" not in record) or ("name" in record and _teaql_is_null(record["name"])):
            results.append(CheckResult("required", ObjectLocation().property("name")))
        if "name" in record and _teaql_raw(record["name"]) is not None and len(_teaql_raw(record["name"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("name"), _teaql_raw(record["name"]), 100))

        if (operation == "insert" and "base_url" not in record) or ("base_url" in record and _teaql_is_null(record["base_url"])):
            results.append(CheckResult("required", ObjectLocation().property("base_url")))
        if "base_url" in record and _teaql_raw(record["base_url"]) is not None and len(_teaql_raw(record["base_url"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("base_url"), _teaql_raw(record["base_url"]), 100))

        if (operation == "insert" and "create_time" not in record) or ("create_time" in record and _teaql_is_null(record["create_time"])):
            results.append(CheckResult("required", ObjectLocation().property("create_time")))

        if (operation == "insert" and "update_time" not in record) or ("update_time" in record and _teaql_is_null(record["update_time"])):
            results.append(CheckResult("required", ObjectLocation().property("update_time")))



class _SchoolTypeChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        now = context.get_resource("fix_time")
        if (operation == "insert" and "platform" not in record) or ("platform" in record and _teaql_is_null(record["platform"])):
            results.append(CheckResult("required", ObjectLocation().property("platform")))


        if (operation == "insert" and "name" not in record) or ("name" in record and _teaql_is_null(record["name"])):
            results.append(CheckResult("required", ObjectLocation().property("name")))
        if "name" in record and _teaql_raw(record["name"]) is not None and len(_teaql_raw(record["name"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("name"), _teaql_raw(record["name"]), 100))

        if (operation == "insert" and "code" not in record) or ("code" in record and _teaql_is_null(record["code"])):
            results.append(CheckResult("required", ObjectLocation().property("code")))
        if "code" in record and _teaql_raw(record["code"]) is not None and len(_teaql_raw(record["code"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("code"), _teaql_raw(record["code"]), 100))

        if (operation == "insert" and "display_order" not in record) or ("display_order" in record and _teaql_is_null(record["display_order"])):
            results.append(CheckResult("required", ObjectLocation().property("display_order")))



class _SchoolChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        now = context.get_resource("fix_time")
        if operation == "insert" and ("create_time" not in record or _teaql_is_null(record["create_time"])):
            record["create_time"] = Value.from_any(now)
            context.record_fix_evidence("School", "create_time", "clock", "graphClock")

        if operation == "insert" and ("update_time" not in record or _teaql_is_null(record["update_time"])):
            record["update_time"] = Value.from_any(now)
            context.record_fix_evidence("School", "update_time", "clock", "graphClock")
        if operation == "insert" or operation == "update":
            record["update_time"] = Value.from_any(now)
            context.record_fix_evidence("School", "update_time", "clock", "graphClock")


        if (operation == "insert" and "platform" not in record) or ("platform" in record and _teaql_is_null(record["platform"])):
            results.append(CheckResult("required", ObjectLocation().property("platform")))

        if (operation == "insert" and "school_type" not in record) or ("school_type" in record and _teaql_is_null(record["school_type"])):
            results.append(CheckResult("required", ObjectLocation().property("school_type")))

        if (operation == "insert" and "name" not in record) or ("name" in record and _teaql_is_null(record["name"])):
            results.append(CheckResult("required", ObjectLocation().property("name")))
        if "name" in record and _teaql_raw(record["name"]) is not None and len(_teaql_raw(record["name"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("name"), _teaql_raw(record["name"]), 100))

        if (operation == "insert" and "address" not in record) or ("address" in record and _teaql_is_null(record["address"])):
            results.append(CheckResult("required", ObjectLocation().property("address")))
        if "address" in record and _teaql_raw(record["address"]) is not None and len(_teaql_raw(record["address"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("address"), _teaql_raw(record["address"]), 100))

        if (operation == "insert" and "established_date" not in record) or ("established_date" in record and _teaql_is_null(record["established_date"])):
            results.append(CheckResult("required", ObjectLocation().property("established_date")))

        if (operation == "insert" and "student_capacity" not in record) or ("student_capacity" in record and _teaql_is_null(record["student_capacity"])):
            results.append(CheckResult("required", ObjectLocation().property("student_capacity")))

        if (operation == "insert" and "active" not in record) or ("active" in record and _teaql_is_null(record["active"])):
            results.append(CheckResult("required", ObjectLocation().property("active")))

        if (operation == "insert" and "create_time" not in record) or ("create_time" in record and _teaql_is_null(record["create_time"])):
            results.append(CheckResult("required", ObjectLocation().property("create_time")))

        if (operation == "insert" and "update_time" not in record) or ("update_time" in record and _teaql_is_null(record["update_time"])):
            results.append(CheckResult("required", ObjectLocation().property("update_time")))



_Platform_DESCRIPTOR = (EntityDescriptor("Platform")
    .table_name("platform_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").is_id().required()).property(PropertyDescriptor("name", DataType.Text).column_name("name").required()).property(PropertyDescriptor("base_url", DataType.Text).column_name("base_url").required()).property(PropertyDescriptor("create_time", DataType.Timestamp).column_name("create_time").required()).property(PropertyDescriptor("update_time", DataType.Timestamp).column_name("update_time").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").is_version().required()).relation(RelationDescriptor("school_type_list", "SchoolType").local("id").foreign("platform").many()).relation(RelationDescriptor("school_list", "School").local("id").foreign("platform").many())
)

_SchoolType_DESCRIPTOR = (EntityDescriptor("SchoolType")
    .table_name("school_type_data").property(PropertyDescriptor("platform", DataType.I64).column_name("platform").required()).property(PropertyDescriptor("id", DataType.I64).column_name("id").is_id().required()).property(PropertyDescriptor("name", DataType.Text).column_name("name").required()).property(PropertyDescriptor("code", DataType.Text).column_name("code").required()).property(PropertyDescriptor("display_order", DataType.Decimal).column_name("display_order").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").is_version().required()).relation(RelationDescriptor("platform", "Platform").local("platform").foreign("id")).relation(RelationDescriptor("school_list", "School").local("id").foreign("school_type").many())
)

_School_DESCRIPTOR = (EntityDescriptor("School")
    .table_name("school_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").is_id().required()).property(PropertyDescriptor("platform", DataType.I64).column_name("platform").required()).property(PropertyDescriptor("school_type", DataType.I64).column_name("school_type").required()).property(PropertyDescriptor("name", DataType.Text).column_name("name").required()).property(PropertyDescriptor("address", DataType.Text).column_name("address").required()).property(PropertyDescriptor("established_date", DataType.Date).column_name("established_date").required()).property(PropertyDescriptor("student_capacity", DataType.I64).column_name("student_capacity").required()).property(PropertyDescriptor("active", DataType.Bool).column_name("active").required()).property(PropertyDescriptor("create_time", DataType.Timestamp).column_name("create_time").required()).property(PropertyDescriptor("update_time", DataType.Timestamp).column_name("update_time").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").is_version().required()).relation(RelationDescriptor("platform", "Platform").local("platform").foreign("id")).relation(RelationDescriptor("school_type", "SchoolType").local("school_type").foreign("id"))
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
            platform_1.update_name("Campus Learning Platform")
            platform_1.update_base_url("https://campus.example.com")
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
        school_type_1001 = await (Q.school_types().with_id_is(1001).comment('what: locate generated bootstrap entity').purpose('why: idempotent runtime bootstrap').execute_for_one(context))
        if school_type_1001 is None:
            school_type_1001 = SchoolType._teaql_new_with_fixed_id(1001)
            school_type_1001.update_platform(Platform.refer(1))
            school_type_1001.update_name("Primary")
            school_type_1001.update_code("PRIMARY")
            school_type_1001.update_display_order(1)
            try:
                await school_type_1001.audit_as('create model constant SchoolType(1001)').save(context)
            except Exception as _teaql_create_error:
                for _teaql_attempt in range(5):
                    school_type_1001 = await (Q.school_types().with_id_is(1001).comment('what: recover concurrent bootstrap').purpose('why: make generated bootstrap idempotent').execute_for_one(context))
                    if school_type_1001 is not None:
                        break
                    if _teaql_attempt < 4:
                        await asyncio.sleep((_teaql_attempt + 1) * 0.01)
                if school_type_1001 is None:
                    raise _teaql_create_error
        _teaql_changed = False
        if school_type_1001.platform != 1:
            school_type_1001.update_platform(Platform.refer(1))
            _teaql_changed = True
        if school_type_1001.name != "Primary":
            school_type_1001.update_name("Primary")
            _teaql_changed = True
        if school_type_1001.code != "PRIMARY":
            school_type_1001.update_code("PRIMARY")
            _teaql_changed = True
        if school_type_1001.displayOrder != 1:
            school_type_1001.update_display_order(1)
            _teaql_changed = True
        if _teaql_changed:
            await school_type_1001.audit_as('reconcile model constant SchoolType(1001)').save(context)
        school_type_1002 = await (Q.school_types().with_id_is(1002).comment('what: locate generated bootstrap entity').purpose('why: idempotent runtime bootstrap').execute_for_one(context))
        if school_type_1002 is None:
            school_type_1002 = SchoolType._teaql_new_with_fixed_id(1002)
            school_type_1002.update_platform(Platform.refer(1))
            school_type_1002.update_name("Secondary")
            school_type_1002.update_code("SECONDARY")
            school_type_1002.update_display_order(2)
            try:
                await school_type_1002.audit_as('create model constant SchoolType(1002)').save(context)
            except Exception as _teaql_create_error:
                for _teaql_attempt in range(5):
                    school_type_1002 = await (Q.school_types().with_id_is(1002).comment('what: recover concurrent bootstrap').purpose('why: make generated bootstrap idempotent').execute_for_one(context))
                    if school_type_1002 is not None:
                        break
                    if _teaql_attempt < 4:
                        await asyncio.sleep((_teaql_attempt + 1) * 0.01)
                if school_type_1002 is None:
                    raise _teaql_create_error
        _teaql_changed = False
        if school_type_1002.platform != 1:
            school_type_1002.update_platform(Platform.refer(1))
            _teaql_changed = True
        if school_type_1002.name != "Secondary":
            school_type_1002.update_name("Secondary")
            _teaql_changed = True
        if school_type_1002.code != "SECONDARY":
            school_type_1002.update_code("SECONDARY")
            _teaql_changed = True
        if school_type_1002.displayOrder != 2:
            school_type_1002.update_display_order(2)
            _teaql_changed = True
        if _teaql_changed:
            await school_type_1002.audit_as('reconcile model constant SchoolType(1002)').save(context)
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
    .wire_metadata("Platform", create_wire_entity_metadata("Platform", ["id", "name", "base_url", "create_time", "update_time", "version"], JsonFieldNamingProfile.CAMEL_CASE, {"id": ["id"], "name": ["name"], "base_url": ["base_url"], "create_time": ["create_time"], "update_time": ["update_time"], "version": ["version"]})).entity(SchoolType)
    .schema_entity(_SchoolType_DESCRIPTOR)
    .checker("SchoolType", _SchoolTypeChecker())
    .wire_metadata("SchoolType", create_wire_entity_metadata("SchoolType", ["platform", "id", "name", "code", "display_order", "version"], JsonFieldNamingProfile.CAMEL_CASE, {"platform": ["platform"], "id": ["id"], "name": ["name"], "code": ["code"], "display_order": ["display_order"], "version": ["version"]})).entity(School)
    .schema_entity(_School_DESCRIPTOR)
    .checker("School", _SchoolChecker())
    .wire_metadata("School", create_wire_entity_metadata("School", ["id", "platform", "school_type", "name", "address", "established_date", "student_capacity", "active", "create_time", "update_time", "version"], JsonFieldNamingProfile.CAMEL_CASE, {"id": ["id"], "platform": ["platform"], "school_type": ["school_type"], "name": ["name"], "address": ["address"], "established_date": ["established_date"], "student_capacity": ["student_capacity"], "active": ["active"], "create_time": ["create_time"], "update_time": ["update_time"], "version": ["version"]}))
    .generated_bootstrap(_ensure_generated_bootstrap)
)