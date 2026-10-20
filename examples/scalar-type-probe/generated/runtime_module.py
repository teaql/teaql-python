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
from models.type_platform import TypePlatform
from models.scalar_type_probe import ScalarTypeProbe

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

class _TypePlatformChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        now = context.get_resource("fix_time")
        if (operation == "insert" and "name" not in record) or ("name" in record and _teaql_is_null(record["name"])):
            results.append(CheckResult("required", ObjectLocation().property("name")))
        if "name" in record and _teaql_raw(record["name"]) is not None and len(_teaql_raw(record["name"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("name"), _teaql_raw(record["name"]), 100))



class _ScalarTypeProbeChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        now = context.get_resource("fix_time")
        if operation == "insert" and ("create_time" not in record or _teaql_is_null(record["create_time"])):
            record["create_time"] = Value.from_any(now)
            context.record_fix_evidence("ScalarTypeProbe", "create_time", "clock", "graphClock")

        if operation == "insert" and ("update_time" not in record or _teaql_is_null(record["update_time"])):
            record["update_time"] = Value.from_any(now)
            context.record_fix_evidence("ScalarTypeProbe", "update_time", "clock", "graphClock")
        if operation == "insert" or operation == "update":
            record["update_time"] = Value.from_any(now)
            context.record_fix_evidence("ScalarTypeProbe", "update_time", "clock", "graphClock")


        if (operation == "insert" and "type_platform" not in record) or ("type_platform" in record and _teaql_is_null(record["type_platform"])):
            results.append(CheckResult("required", ObjectLocation().property("type_platform")))

        if (operation == "insert" and "required_string" not in record) or ("required_string" in record and _teaql_is_null(record["required_string"])):
            results.append(CheckResult("required", ObjectLocation().property("required_string")))
        if "required_string" in record and _teaql_raw(record["required_string"]) is not None and len(_teaql_raw(record["required_string"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("required_string"), _teaql_raw(record["required_string"]), 100))

        if "optional_string" in record and _teaql_raw(record["optional_string"]) is not None and len(_teaql_raw(record["optional_string"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("optional_string"), _teaql_raw(record["optional_string"]), 100))


        if (operation == "insert" and "required_boolean" not in record) or ("required_boolean" in record and _teaql_is_null(record["required_boolean"])):
            results.append(CheckResult("required", ObjectLocation().property("required_boolean")))


        if (operation == "insert" and "required_integer" not in record) or ("required_integer" in record and _teaql_is_null(record["required_integer"])):
            results.append(CheckResult("required", ObjectLocation().property("required_integer")))


        if (operation == "insert" and "required_long" not in record) or ("required_long" in record and _teaql_is_null(record["required_long"])):
            results.append(CheckResult("required", ObjectLocation().property("required_long")))


        if (operation == "insert" and "required_decimal" not in record) or ("required_decimal" in record and _teaql_is_null(record["required_decimal"])):
            results.append(CheckResult("required", ObjectLocation().property("required_decimal")))


        if (operation == "insert" and "required_float" not in record) or ("required_float" in record and _teaql_is_null(record["required_float"])):
            results.append(CheckResult("required", ObjectLocation().property("required_float")))


        if (operation == "insert" and "required_double" not in record) or ("required_double" in record and _teaql_is_null(record["required_double"])):
            results.append(CheckResult("required", ObjectLocation().property("required_double")))


        if (operation == "insert" and "required_date" not in record) or ("required_date" in record and _teaql_is_null(record["required_date"])):
            results.append(CheckResult("required", ObjectLocation().property("required_date")))


        if (operation == "insert" and "required_time" not in record) or ("required_time" in record and _teaql_is_null(record["required_time"])):
            results.append(CheckResult("required", ObjectLocation().property("required_time")))


        if (operation == "insert" and "required_datetime" not in record) or ("required_datetime" in record and _teaql_is_null(record["required_datetime"])):
            results.append(CheckResult("required", ObjectLocation().property("required_datetime")))


        if (operation == "insert" and "create_time" not in record) or ("create_time" in record and _teaql_is_null(record["create_time"])):
            results.append(CheckResult("required", ObjectLocation().property("create_time")))

        if (operation == "insert" and "update_time" not in record) or ("update_time" in record and _teaql_is_null(record["update_time"])):
            results.append(CheckResult("required", ObjectLocation().property("update_time")))



_TypePlatform_DESCRIPTOR = (EntityDescriptor("TypePlatform")
    .audit_mask_fields([])
    .table_name("type_platform_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("name", DataType.Text).column_name("name").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("scalar_type_probe_list", "ScalarTypeProbe").local("id").foreign("type_platform").many())
)

_ScalarTypeProbe_DESCRIPTOR = (EntityDescriptor("ScalarTypeProbe")
    .audit_mask_fields([])
    .table_name("scalar_type_probe_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("type_platform", DataType.I64).column_name("type_platform").log_policy("plain").required()).property(PropertyDescriptor("required_string", DataType.Text).column_name("required_string").log_policy("plain").required()).property(PropertyDescriptor("optional_string", DataType.Text).column_name("optional_string").log_policy("plain")).property(PropertyDescriptor("large_text", DataType.Text).column_name("large_text").log_policy("plain")).property(PropertyDescriptor("required_boolean", DataType.Bool).column_name("required_boolean").log_policy("plain").required()).property(PropertyDescriptor("optional_boolean", DataType.Bool).column_name("optional_boolean").log_policy("plain")).property(PropertyDescriptor("required_integer", DataType.I64).column_name("required_integer").log_policy("plain").required()).property(PropertyDescriptor("optional_integer", DataType.I64).column_name("optional_integer").log_policy("plain")).property(PropertyDescriptor("required_long", DataType.I64).column_name("required_long").log_policy("plain").required()).property(PropertyDescriptor("optional_long", DataType.I64).column_name("optional_long").log_policy("plain")).property(PropertyDescriptor("required_decimal", DataType.Decimal).column_name("required_decimal").log_policy("plain").required()).property(PropertyDescriptor("optional_decimal", DataType.Decimal).column_name("optional_decimal").log_policy("plain")).property(PropertyDescriptor("required_float", DataType.F64).column_name("required_float").log_policy("plain").required()).property(PropertyDescriptor("optional_float", DataType.F64).column_name("optional_float").log_policy("plain")).property(PropertyDescriptor("required_double", DataType.F64).column_name("required_double").log_policy("plain").required()).property(PropertyDescriptor("optional_double", DataType.F64).column_name("optional_double").log_policy("plain")).property(PropertyDescriptor("required_date", DataType.Date).column_name("required_date").log_policy("plain").required()).property(PropertyDescriptor("optional_date", DataType.Date).column_name("optional_date").log_policy("plain")).property(PropertyDescriptor("required_time", DataType.Time).column_name("required_time").log_policy("plain").required()).property(PropertyDescriptor("optional_time", DataType.Time).column_name("optional_time").log_policy("plain")).property(PropertyDescriptor("required_datetime", DataType.Timestamp).column_name("required_datetime").log_policy("plain").required()).property(PropertyDescriptor("optional_datetime", DataType.Timestamp).column_name("optional_datetime").log_policy("plain")).property(PropertyDescriptor("create_time", DataType.Timestamp).column_name("create_time").log_policy("plain").required()).property(PropertyDescriptor("update_time", DataType.Timestamp).column_name("update_time").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("type_platform", "TypePlatform").local("type_platform").foreign("id"))
)

async def _ensure_generated_bootstrap_once(context):
    previous_actor = context.user_identifier() if hasattr(context, 'user_identifier') else None
    previous_category = context.get_resource('bootstrapCategory')
    if hasattr(context, 'set_user_identifier'):
        context.set_user_identifier('teaql-generated-bootstrap')
    context.insert_resource('bootstrapCategory', 'runtime-bootstrap')
    try:
        type_platform_1 = await (Q.type_platforms().with_id_is(1).comment('what: locate generated bootstrap entity').purpose('why: idempotent runtime bootstrap').execute_for_one(context))
        if type_platform_1 is None:
            type_platform_1 = TypePlatform._teaql_new_with_fixed_id(1)
            type_platform_1.update_name("Scalar Type Conformance")
            try:
                await type_platform_1.audit_as('create model root TypePlatform(1)').save(context)
            except Exception as _teaql_create_error:
                for _teaql_attempt in range(5):
                    type_platform_1 = await (Q.type_platforms().with_id_is(1).comment('what: recover concurrent bootstrap').purpose('why: make generated bootstrap idempotent').execute_for_one(context))
                    if type_platform_1 is not None:
                        break
                    if _teaql_attempt < 4:
                        await asyncio.sleep((_teaql_attempt + 1) * 0.01)
                if type_platform_1 is None:
                    raise _teaql_create_error
        context.with_active_root(ContextEntityRef("TypePlatform", 1))
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
GENERATED_RUNTIME_MODULE = (RuntimeModule().entity(TypePlatform)
    .schema_entity(_TypePlatform_DESCRIPTOR)
    .checker("TypePlatform", _TypePlatformChecker())
    .wire_metadata("TypePlatform", create_wire_entity_metadata("TypePlatform", ["id", "name", "version"], JsonFieldNamingProfile.CAMEL_CASE, {"id": ["id"], "name": ["name"], "version": ["version"]})).entity(ScalarTypeProbe)
    .schema_entity(_ScalarTypeProbe_DESCRIPTOR)
    .checker("ScalarTypeProbe", _ScalarTypeProbeChecker())
    .wire_metadata("ScalarTypeProbe", create_wire_entity_metadata("ScalarTypeProbe", ["id", "type_platform", "required_string", "optional_string", "large_text", "required_boolean", "optional_boolean", "required_integer", "optional_integer", "required_long", "optional_long", "required_decimal", "optional_decimal", "required_float", "optional_float", "required_double", "optional_double", "required_date", "optional_date", "required_time", "optional_time", "required_datetime", "optional_datetime", "create_time", "update_time", "version"], JsonFieldNamingProfile.CAMEL_CASE, {"id": ["id"], "type_platform": ["type_platform"], "required_string": ["required_string"], "optional_string": ["optional_string"], "large_text": ["large_text"], "required_boolean": ["required_boolean"], "optional_boolean": ["optional_boolean"], "required_integer": ["required_integer"], "optional_integer": ["optional_integer"], "required_long": ["required_long"], "optional_long": ["optional_long"], "required_decimal": ["required_decimal"], "optional_decimal": ["optional_decimal"], "required_float": ["required_float"], "optional_float": ["optional_float"], "required_double": ["required_double"], "optional_double": ["optional_double"], "required_date": ["required_date"], "optional_date": ["optional_date"], "required_time": ["required_time"], "optional_time": ["optional_time"], "required_datetime": ["required_datetime"], "optional_datetime": ["optional_datetime"], "create_time": ["create_time"], "update_time": ["update_time"], "version": ["version"]}))
    .generated_bootstrap(_ensure_generated_bootstrap)
)