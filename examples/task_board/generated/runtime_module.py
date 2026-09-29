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
from models.task_status import TaskStatus
from models.task import Task
from models.task_execution_log import TaskExecutionLog

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
        if operation == "insert" and ("founded" not in record or _teaql_is_null(record["founded"])):
            record["founded"] = Value.from_any(now)
            context.record_fix_evidence("Platform", "founded", "clock", "graphClock")



        if (operation == "insert" and "name" not in record) or ("name" in record and _teaql_is_null(record["name"])):
            results.append(CheckResult("required", ObjectLocation().property("name")))
        if "name" in record and _teaql_raw(record["name"]) is not None and len(_teaql_raw(record["name"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("name"), _teaql_raw(record["name"]), 100))

        if (operation == "insert" and "founded" not in record) or ("founded" in record and _teaql_is_null(record["founded"])):
            results.append(CheckResult("required", ObjectLocation().property("founded")))

        if (operation == "insert" and "user_email" not in record) or ("user_email" in record and _teaql_is_null(record["user_email"])):
            results.append(CheckResult("required", ObjectLocation().property("user_email")))
        if "user_email" in record and _teaql_raw(record["user_email"]) is not None and len(_teaql_raw(record["user_email"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("user_email"), _teaql_raw(record["user_email"]), 100))



class _TaskStatusChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        now = context.get_resource("fix_time")
        if (operation == "insert" and "name" not in record) or ("name" in record and _teaql_is_null(record["name"])):
            results.append(CheckResult("required", ObjectLocation().property("name")))
        if "name" in record and _teaql_raw(record["name"]) is not None and len(_teaql_raw(record["name"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("name"), _teaql_raw(record["name"]), 100))

        if (operation == "insert" and "code" not in record) or ("code" in record and _teaql_is_null(record["code"])):
            results.append(CheckResult("required", ObjectLocation().property("code")))
        if "code" in record and _teaql_raw(record["code"]) is not None and len(_teaql_raw(record["code"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("code"), _teaql_raw(record["code"]), 100))

        if (operation == "insert" and "color" not in record) or ("color" in record and _teaql_is_null(record["color"])):
            results.append(CheckResult("required", ObjectLocation().property("color")))
        if "color" in record and _teaql_raw(record["color"]) is not None and len(_teaql_raw(record["color"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("color"), _teaql_raw(record["color"]), 100))

        if (operation == "insert" and "display_order" not in record) or ("display_order" in record and _teaql_is_null(record["display_order"])):
            results.append(CheckResult("required", ObjectLocation().property("display_order")))

        if (operation == "insert" and "progress" not in record) or ("progress" in record and _teaql_is_null(record["progress"])):
            results.append(CheckResult("required", ObjectLocation().property("progress")))

        if (operation == "insert" and "platform" not in record) or ("platform" in record and _teaql_is_null(record["platform"])):
            results.append(CheckResult("required", ObjectLocation().property("platform")))



class _TaskChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        now = context.get_resource("fix_time")
        if (operation == "insert" and "name" not in record) or ("name" in record and _teaql_is_null(record["name"])):
            results.append(CheckResult("required", ObjectLocation().property("name")))
        if "name" in record and _teaql_raw(record["name"]) is not None and not len(_teaql_raw(record["name"])) >= 1:
            results.append(CheckResult("min_length", ObjectLocation().property("name"), _teaql_raw(record["name"]), 1))
        if "name" in record and _teaql_raw(record["name"]) is not None and len(_teaql_raw(record["name"])) > 200:
            results.append(CheckResult("max_length", ObjectLocation().property("name"), _teaql_raw(record["name"]), 200))

        if (operation == "insert" and "status" not in record) or ("status" in record and _teaql_is_null(record["status"])):
            results.append(CheckResult("required", ObjectLocation().property("status")))

        if (operation == "insert" and "platform" not in record) or ("platform" in record and _teaql_is_null(record["platform"])):
            results.append(CheckResult("required", ObjectLocation().property("platform")))



class _TaskExecutionLogChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        now = context.get_resource("fix_time")
        if (operation == "insert" and "task" not in record) or ("task" in record and _teaql_is_null(record["task"])):
            results.append(CheckResult("required", ObjectLocation().property("task")))

        if (operation == "insert" and "action" not in record) or ("action" in record and _teaql_is_null(record["action"])):
            results.append(CheckResult("required", ObjectLocation().property("action")))
        if "action" in record and _teaql_raw(record["action"]) is not None and len(_teaql_raw(record["action"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("action"), _teaql_raw(record["action"]), 100))

        if (operation == "insert" and "detail" not in record) or ("detail" in record and _teaql_is_null(record["detail"])):
            results.append(CheckResult("required", ObjectLocation().property("detail")))
        if "detail" in record and _teaql_raw(record["detail"]) is not None and len(_teaql_raw(record["detail"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("detail"), _teaql_raw(record["detail"]), 100))



_Platform_DESCRIPTOR = (EntityDescriptor("Platform")
    .audit_mask_fields([])
    .table_name("platform_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("name", DataType.Text).column_name("name").log_policy("plain").required()).property(PropertyDescriptor("founded", DataType.Timestamp).column_name("founded").log_policy("plain").required()).property(PropertyDescriptor("user_email", DataType.Text).column_name("user_email").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("task_status_list", "TaskStatus").local("id").foreign("platform").many()).relation(RelationDescriptor("task_list", "Task").local("id").foreign("platform").many())
)

_TaskStatus_DESCRIPTOR = (EntityDescriptor("TaskStatus")
    .audit_mask_fields([])
    .table_name("task_status_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("name", DataType.Text).column_name("name").log_policy("plain").required()).property(PropertyDescriptor("code", DataType.Text).column_name("code").log_policy("plain").required()).property(PropertyDescriptor("color", DataType.Text).column_name("color").log_policy("plain").required()).property(PropertyDescriptor("display_order", DataType.Decimal).column_name("display_order").log_policy("plain").required()).property(PropertyDescriptor("progress", DataType.Decimal).column_name("progress").log_policy("plain").required()).property(PropertyDescriptor("platform", DataType.I64).column_name("platform").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("platform", "Platform").local("platform").foreign("id")).relation(RelationDescriptor("task_list", "Task").local("id").foreign("status").many())
)

_Task_DESCRIPTOR = (EntityDescriptor("Task")
    .audit_mask_fields([])
    .table_name("task_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("name", DataType.Text).column_name("name").log_policy("plain").required()).property(PropertyDescriptor("status", DataType.I64).column_name("status").log_policy("plain").required()).property(PropertyDescriptor("platform", DataType.I64).column_name("platform").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("status", "TaskStatus").local("status").foreign("id")).relation(RelationDescriptor("platform", "Platform").local("platform").foreign("id")).relation(RelationDescriptor("task_execution_log_list", "TaskExecutionLog").local("id").foreign("task").many())
)

_TaskExecutionLog_DESCRIPTOR = (EntityDescriptor("TaskExecutionLog")
    .audit_mask_fields(["detail"])
    .table_name("task_execution_log_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("task", DataType.I64).column_name("task").log_policy("plain").required()).property(PropertyDescriptor("action", DataType.Text).column_name("action").log_policy("plain").required()).property(PropertyDescriptor("detail", DataType.Text).column_name("detail").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("task", "Task").local("task").foreign("id"))
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
            platform_1.update_name("Robot System")
            platform_1.update_user_email("string()")
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
        task_status_1001 = await (Q.task_statuses().with_id_is(1001).comment('what: locate generated bootstrap entity').purpose('why: idempotent runtime bootstrap').execute_for_one(context))
        if task_status_1001 is None:
            task_status_1001 = TaskStatus._teaql_new_with_fixed_id(1001)
            task_status_1001.update_name("Planned")
            task_status_1001.update_code("PLANNED")
            task_status_1001.update_color("#94A3B8")
            task_status_1001.update_display_order(10)
            task_status_1001.update_progress(0)
            task_status_1001.update_platform(Platform.refer(1))
            try:
                await task_status_1001.audit_as('create model constant TaskStatus(1001)').save(context)
            except Exception as _teaql_create_error:
                for _teaql_attempt in range(5):
                    task_status_1001 = await (Q.task_statuses().with_id_is(1001).comment('what: recover concurrent bootstrap').purpose('why: make generated bootstrap idempotent').execute_for_one(context))
                    if task_status_1001 is not None:
                        break
                    if _teaql_attempt < 4:
                        await asyncio.sleep((_teaql_attempt + 1) * 0.01)
                if task_status_1001 is None:
                    raise _teaql_create_error
        _teaql_changed = False
        if task_status_1001.name != "Planned":
            task_status_1001.update_name("Planned")
            _teaql_changed = True
        if task_status_1001.code != "PLANNED":
            task_status_1001.update_code("PLANNED")
            _teaql_changed = True
        if task_status_1001.color != "#94A3B8":
            task_status_1001.update_color("#94A3B8")
            _teaql_changed = True
        if task_status_1001.displayOrder != 10:
            task_status_1001.update_display_order(10)
            _teaql_changed = True
        if task_status_1001.progress != 0:
            task_status_1001.update_progress(0)
            _teaql_changed = True
        if task_status_1001.platform != 1:
            task_status_1001.update_platform(Platform.refer(1))
            _teaql_changed = True
        if _teaql_changed:
            await task_status_1001.audit_as('reconcile model constant TaskStatus(1001)').save(context)
        task_status_1002 = await (Q.task_statuses().with_id_is(1002).comment('what: locate generated bootstrap entity').purpose('why: idempotent runtime bootstrap').execute_for_one(context))
        if task_status_1002 is None:
            task_status_1002 = TaskStatus._teaql_new_with_fixed_id(1002)
            task_status_1002.update_name("Ready")
            task_status_1002.update_code("READY")
            task_status_1002.update_color("#3B82F6")
            task_status_1002.update_display_order(20)
            task_status_1002.update_progress(25)
            task_status_1002.update_platform(Platform.refer(1))
            try:
                await task_status_1002.audit_as('create model constant TaskStatus(1002)').save(context)
            except Exception as _teaql_create_error:
                for _teaql_attempt in range(5):
                    task_status_1002 = await (Q.task_statuses().with_id_is(1002).comment('what: recover concurrent bootstrap').purpose('why: make generated bootstrap idempotent').execute_for_one(context))
                    if task_status_1002 is not None:
                        break
                    if _teaql_attempt < 4:
                        await asyncio.sleep((_teaql_attempt + 1) * 0.01)
                if task_status_1002 is None:
                    raise _teaql_create_error
        _teaql_changed = False
        if task_status_1002.name != "Ready":
            task_status_1002.update_name("Ready")
            _teaql_changed = True
        if task_status_1002.code != "READY":
            task_status_1002.update_code("READY")
            _teaql_changed = True
        if task_status_1002.color != "#3B82F6":
            task_status_1002.update_color("#3B82F6")
            _teaql_changed = True
        if task_status_1002.displayOrder != 20:
            task_status_1002.update_display_order(20)
            _teaql_changed = True
        if task_status_1002.progress != 25:
            task_status_1002.update_progress(25)
            _teaql_changed = True
        if task_status_1002.platform != 1:
            task_status_1002.update_platform(Platform.refer(1))
            _teaql_changed = True
        if _teaql_changed:
            await task_status_1002.audit_as('reconcile model constant TaskStatus(1002)').save(context)
        task_status_1003 = await (Q.task_statuses().with_id_is(1003).comment('what: locate generated bootstrap entity').purpose('why: idempotent runtime bootstrap').execute_for_one(context))
        if task_status_1003 is None:
            task_status_1003 = TaskStatus._teaql_new_with_fixed_id(1003)
            task_status_1003.update_name("Executing")
            task_status_1003.update_code("EXECUTING")
            task_status_1003.update_color("#F59E0B")
            task_status_1003.update_display_order(30)
            task_status_1003.update_progress(50)
            task_status_1003.update_platform(Platform.refer(1))
            try:
                await task_status_1003.audit_as('create model constant TaskStatus(1003)').save(context)
            except Exception as _teaql_create_error:
                for _teaql_attempt in range(5):
                    task_status_1003 = await (Q.task_statuses().with_id_is(1003).comment('what: recover concurrent bootstrap').purpose('why: make generated bootstrap idempotent').execute_for_one(context))
                    if task_status_1003 is not None:
                        break
                    if _teaql_attempt < 4:
                        await asyncio.sleep((_teaql_attempt + 1) * 0.01)
                if task_status_1003 is None:
                    raise _teaql_create_error
        _teaql_changed = False
        if task_status_1003.name != "Executing":
            task_status_1003.update_name("Executing")
            _teaql_changed = True
        if task_status_1003.code != "EXECUTING":
            task_status_1003.update_code("EXECUTING")
            _teaql_changed = True
        if task_status_1003.color != "#F59E0B":
            task_status_1003.update_color("#F59E0B")
            _teaql_changed = True
        if task_status_1003.displayOrder != 30:
            task_status_1003.update_display_order(30)
            _teaql_changed = True
        if task_status_1003.progress != 50:
            task_status_1003.update_progress(50)
            _teaql_changed = True
        if task_status_1003.platform != 1:
            task_status_1003.update_platform(Platform.refer(1))
            _teaql_changed = True
        if _teaql_changed:
            await task_status_1003.audit_as('reconcile model constant TaskStatus(1003)').save(context)
        task_status_1004 = await (Q.task_statuses().with_id_is(1004).comment('what: locate generated bootstrap entity').purpose('why: idempotent runtime bootstrap').execute_for_one(context))
        if task_status_1004 is None:
            task_status_1004 = TaskStatus._teaql_new_with_fixed_id(1004)
            task_status_1004.update_name("Verified")
            task_status_1004.update_code("VERIFIED")
            task_status_1004.update_color("#16A34A")
            task_status_1004.update_display_order(40)
            task_status_1004.update_progress(100)
            task_status_1004.update_platform(Platform.refer(1))
            try:
                await task_status_1004.audit_as('create model constant TaskStatus(1004)').save(context)
            except Exception as _teaql_create_error:
                for _teaql_attempt in range(5):
                    task_status_1004 = await (Q.task_statuses().with_id_is(1004).comment('what: recover concurrent bootstrap').purpose('why: make generated bootstrap idempotent').execute_for_one(context))
                    if task_status_1004 is not None:
                        break
                    if _teaql_attempt < 4:
                        await asyncio.sleep((_teaql_attempt + 1) * 0.01)
                if task_status_1004 is None:
                    raise _teaql_create_error
        _teaql_changed = False
        if task_status_1004.name != "Verified":
            task_status_1004.update_name("Verified")
            _teaql_changed = True
        if task_status_1004.code != "VERIFIED":
            task_status_1004.update_code("VERIFIED")
            _teaql_changed = True
        if task_status_1004.color != "#16A34A":
            task_status_1004.update_color("#16A34A")
            _teaql_changed = True
        if task_status_1004.displayOrder != 40:
            task_status_1004.update_display_order(40)
            _teaql_changed = True
        if task_status_1004.progress != 100:
            task_status_1004.update_progress(100)
            _teaql_changed = True
        if task_status_1004.platform != 1:
            task_status_1004.update_platform(Platform.refer(1))
            _teaql_changed = True
        if _teaql_changed:
            await task_status_1004.audit_as('reconcile model constant TaskStatus(1004)').save(context)
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
    .wire_metadata("Platform", create_wire_entity_metadata("Platform", ["id", "name", "founded", "user_email", "version"], JsonFieldNamingProfile.CAMEL_CASE, {"id": ["id"], "name": ["name"], "founded": ["founded"], "user_email": ["user_email"], "version": ["version"]})).entity(TaskStatus)
    .schema_entity(_TaskStatus_DESCRIPTOR)
    .checker("TaskStatus", _TaskStatusChecker())
    .wire_metadata("TaskStatus", create_wire_entity_metadata("TaskStatus", ["id", "name", "code", "color", "display_order", "progress", "platform", "version"], JsonFieldNamingProfile.CAMEL_CASE, {"id": ["id"], "name": ["name"], "code": ["code"], "color": ["color"], "display_order": ["display_order"], "progress": ["progress"], "platform": ["platform"], "version": ["version"]})).entity(Task)
    .schema_entity(_Task_DESCRIPTOR)
    .checker("Task", _TaskChecker())
    .wire_metadata("Task", create_wire_entity_metadata("Task", ["id", "name", "status", "platform", "version"], JsonFieldNamingProfile.CAMEL_CASE, {"id": ["id"], "name": ["name"], "status": ["status"], "platform": ["platform"], "version": ["version"]})).entity(TaskExecutionLog)
    .schema_entity(_TaskExecutionLog_DESCRIPTOR)
    .checker("TaskExecutionLog", _TaskExecutionLogChecker())
    .wire_metadata("TaskExecutionLog", create_wire_entity_metadata("TaskExecutionLog", ["id", "task", "action", "detail", "version"], JsonFieldNamingProfile.CAMEL_CASE, {"id": ["id"], "task": ["task"], "action": ["action"], "detail": ["detail"], "version": ["version"]}))
    .generated_bootstrap(_ensure_generated_bootstrap)
)