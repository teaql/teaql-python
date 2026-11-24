import asyncio
from datetime import datetime, timezone
from teaql.runtime import CheckResult, ContextFix, ContextEntityRef, JsonFieldNamingProfile, ObjectLocation, RuntimeModule, create_wire_entity_metadata
from teaql.runtime import CheckerPresentationModel
from teaql.core import BusinessIdErrorCode
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
from models.purchase_order import PurchaseOrder

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
        if (operation == "insert" and "name" not in record) or ("name" in record and _teaql_is_null(record["name"])):
            results.append(CheckResult("required", ObjectLocation().property("name")))
        if "name" in record and _teaql_raw(record["name"]) is not None and len(_teaql_raw(record["name"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("name"), _teaql_raw(record["name"]), 100))



class _PurchaseOrderChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        if (operation == "insert" and "platform" not in record) or ("platform" in record and _teaql_is_null(record["platform"])):
            results.append(CheckResult("required", ObjectLocation().property("platform")))

        if (operation == "insert" and "supplier" not in record) or ("supplier" in record and _teaql_is_null(record["supplier"])):
            results.append(CheckResult("required", ObjectLocation().property("supplier")))
        if "supplier" in record and _teaql_raw(record["supplier"]) is not None and not len(_teaql_raw(record["supplier"])) >= 1:
            results.append(CheckResult("min_length", ObjectLocation().property("supplier"), _teaql_raw(record["supplier"]), 1))
        if "supplier" in record and _teaql_raw(record["supplier"]) is not None and len(_teaql_raw(record["supplier"])) > 80:
            results.append(CheckResult("max_length", ObjectLocation().property("supplier"), _teaql_raw(record["supplier"]), 80))

        if operation == "update" and "order_number" in record:
            results.append(CheckResult(BusinessIdErrorCode.IMMUTABLE.value, ObjectLocation().property("order_number"), message="Business ID is immutable after create"))
        if (operation == "insert" and "order_number" not in record) or ("order_number" in record and _teaql_is_null(record["order_number"])):
            results.append(CheckResult("required", ObjectLocation().property("order_number")))
        if "order_number" in record and _teaql_raw(record["order_number"]) is not None and len(_teaql_raw(record["order_number"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("order_number"), _teaql_raw(record["order_number"]), 100))



_Platform_DESCRIPTOR = (EntityDescriptor("Platform")
    .audit_mask_fields([])
    .table_name("platform_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("name", DataType.Text).column_name("name").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("purchase_order_list", "PurchaseOrder").local("id").foreign("platform").many())
)

_PurchaseOrder_DESCRIPTOR = (EntityDescriptor("PurchaseOrder")
    .audit_mask_fields([])
    .table_name("purchase_order_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("platform", DataType.I64).column_name("platform").log_policy("plain").required()).property(PropertyDescriptor("supplier", DataType.Text).column_name("supplier").log_policy("plain").required()).property(PropertyDescriptor("order_number", DataType.Text).column_name("order_number").log_policy("plain").required().fixed_by_runtime(insert=True)).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("platform", "Platform").local("platform").foreign("id"))
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
            platform_1 = await Q.platforms().comment('reserve generated bootstrap identity').purpose('create a managed bootstrap entity').new_entity(context)
            platform_1.update_id(1)
            platform_1.update_name("Procurement")
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
_CHECKER_PRESENTATION = CheckerPresentationModel.from_json("{\"schema\":\"teaql.checker-model/v1\",\"revision\":\"sha256:304c22e5b2a924d8fc32148174ef6d249857e8080ea8459c2cb4d8a6fd75ae60\",\"entities\":{\"Platform\":{\"labels\":{\"en\":\"platform\"},\"fields\":[{\"name\":\"id\",\"labels\":{\"en\":\"id\"},\"aliases\":[\"Id\"]},{\"name\":\"name\",\"labels\":{\"en\":\"name\"},\"aliases\":[\"Name\"]},{\"name\":\"purchase_order_list\",\"targetType\":\"PurchaseOrder\",\"labels\":{\"en\":\"purchase order\"},\"aliases\":[\"PurchaseOrderList\",\"purchaseOrderList\"]},{\"name\":\"version\",\"labels\":{\"en\":\"version\"},\"aliases\":[\"Version\"]}]},\"PurchaseOrder\":{\"labels\":{\"en\":\"purchase order\"},\"fields\":[{\"name\":\"id\",\"labels\":{\"en\":\"id\"},\"aliases\":[\"Id\"]},{\"name\":\"order_number\",\"labels\":{\"en\":\"order number\"},\"aliases\":[\"OrderNumber\",\"orderNumber\"]},{\"name\":\"platform\",\"targetType\":\"Platform\",\"labels\":{\"en\":\"platform\"},\"aliases\":[\"Platform\"]},{\"name\":\"supplier\",\"labels\":{\"en\":\"supplier\"},\"aliases\":[\"Supplier\"]},{\"name\":\"version\",\"labels\":{\"en\":\"version\"},\"aliases\":[\"Version\"]}]}}}")
GENERATED_RUNTIME_MODULE = (RuntimeModule().entity(Platform)
    .schema_entity(_Platform_DESCRIPTOR)
    .checker("Platform", _PlatformChecker())
    .wire_metadata("Platform", create_wire_entity_metadata("Platform", ["id", "name", "version"], JsonFieldNamingProfile.parse("camelCase"), {"id": ["id"], "name": ["name"], "version": ["version"]})).entity(PurchaseOrder)
    .schema_entity(_PurchaseOrder_DESCRIPTOR)
    .checker("PurchaseOrder", _PurchaseOrderChecker())
    .wire_metadata("PurchaseOrder", create_wire_entity_metadata("PurchaseOrder", ["id", "platform", "supplier", "order_number", "version"], JsonFieldNamingProfile.parse("camelCase"), {"id": ["id"], "platform": ["platform"], "supplier": ["supplier"], "order_number": ["order_number"], "version": ["version"]}))
    .checker_presentation(_CHECKER_PRESENTATION)
    .generated_bootstrap(_ensure_generated_bootstrap)
)