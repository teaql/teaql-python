import asyncio
from datetime import datetime, timezone
from teaql.runtime import CheckResult, ContextFix, ContextEntityRef, JsonFieldNamingProfile, ObjectLocation, RuntimeModule, create_wire_entity_metadata
from teaql.runtime import CheckerPresentationModel
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
from models.warehouse import Warehouse
from models.supplier import Supplier

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

class _WarehouseChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        if (operation == "insert" and "name" not in record) or ("name" in record and _teaql_is_null(record["name"])):
            results.append(CheckResult("required", ObjectLocation().property("name")))
        if "name" in record and _teaql_raw(record["name"]) is not None and len(_teaql_raw(record["name"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("name"), _teaql_raw(record["name"]), 100))



class _SupplierChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        if (operation == "insert" and "warehouse" not in record) or ("warehouse" in record and _teaql_is_null(record["warehouse"])):
            results.append(CheckResult("required", ObjectLocation().property("warehouse")))

        if (operation == "insert" and "name" not in record) or ("name" in record and _teaql_is_null(record["name"])):
            results.append(CheckResult("required", ObjectLocation().property("name")))
        if "name" in record and _teaql_raw(record["name"]) is not None and not len(_teaql_raw(record["name"])) >= 1:
            results.append(CheckResult("min_length", ObjectLocation().property("name"), _teaql_raw(record["name"]), 1))
        if "name" in record and _teaql_raw(record["name"]) is not None and len(_teaql_raw(record["name"])) > 80:
            results.append(CheckResult("max_length", ObjectLocation().property("name"), _teaql_raw(record["name"]), 80))

        if (operation == "insert" and "minimum_order_quantity" not in record) or ("minimum_order_quantity" in record and _teaql_is_null(record["minimum_order_quantity"])):
            results.append(CheckResult("required", ObjectLocation().property("minimum_order_quantity")))
        if "minimum_order_quantity" in record and _teaql_raw(record["minimum_order_quantity"]) is not None and not _teaql_raw(record["minimum_order_quantity"]) >= 10:
            results.append(CheckResult("min", ObjectLocation().property("minimum_order_quantity"), _teaql_raw(record["minimum_order_quantity"]), 10))
        if "minimum_order_quantity" in record and _teaql_raw(record["minimum_order_quantity"]) is not None and _teaql_raw(record["minimum_order_quantity"]) > 10000:
            results.append(CheckResult("max", ObjectLocation().property("minimum_order_quantity"), _teaql_raw(record["minimum_order_quantity"]), 10000))



_Warehouse_DESCRIPTOR = (EntityDescriptor("Warehouse")
    .audit_mask_fields([])
    .table_name("warehouse_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("name", DataType.Text).column_name("name").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("supplier_list", "Supplier").local("id").foreign("warehouse").many())
)

_Supplier_DESCRIPTOR = (EntityDescriptor("Supplier")
    .audit_mask_fields([])
    .table_name("supplier_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("warehouse", DataType.I64).column_name("warehouse").log_policy("plain").required()).property(PropertyDescriptor("name", DataType.Text).column_name("name").log_policy("plain").required()).property(PropertyDescriptor("minimum_order_quantity", DataType.I64).column_name("minimum_order_quantity").log_policy("plain").integer32().required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("warehouse", "Warehouse").local("warehouse").foreign("id"))
)

async def _ensure_generated_bootstrap_once(context):
    previous_actor = context.user_identifier() if hasattr(context, 'user_identifier') else None
    previous_category = context.get_resource('bootstrapCategory')
    if hasattr(context, 'set_user_identifier'):
        context.set_user_identifier('teaql-generated-bootstrap')
    context.insert_resource('bootstrapCategory', 'runtime-bootstrap')
    try:
        warehouse_1 = await (Q.warehouses().with_id_is(1).comment('what: locate generated bootstrap entity').purpose('why: idempotent runtime bootstrap').execute_for_one(context))
        if warehouse_1 is None:
            warehouse_1 = Warehouse._teaql_new_with_fixed_id(1)
            warehouse_1.update_name("Central Warehouse")
            try:
                await warehouse_1.audit_as('create model root Warehouse(1)').save(context)
            except Exception as _teaql_create_error:
                for _teaql_attempt in range(5):
                    warehouse_1 = await (Q.warehouses().with_id_is(1).comment('what: recover concurrent bootstrap').purpose('why: make generated bootstrap idempotent').execute_for_one(context))
                    if warehouse_1 is not None:
                        break
                    if _teaql_attempt < 4:
                        await asyncio.sleep((_teaql_attempt + 1) * 0.01)
                if warehouse_1 is None:
                    raise _teaql_create_error
        context.with_active_root(ContextEntityRef("Warehouse", 1))
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
_CHECKER_PRESENTATION = CheckerPresentationModel.from_json("{\"schema\":\"teaql.checker-model/v1\",\"revision\":\"sha256:f4b63b86dd7cad758f18ebc623d0a4976afb15dbe9f61002523f909bb75098b0\",\"entities\":{\"Supplier\":{\"labels\":{\"en\":\"Supplier\",\"zh-CN\":\"供应商\"},\"fields\":[{\"name\":\"id\",\"labels\":{\"en\":\"id\"},\"aliases\":[\"Id\"]},{\"name\":\"minimum_order_quantity\",\"labels\":{\"en\":\"minimum order quantity\"},\"aliases\":[\"MinimumOrderQuantity\",\"minimumOrderQuantity\"]},{\"name\":\"name\",\"labels\":{\"en\":\"name\"},\"aliases\":[\"Name\"]},{\"name\":\"version\",\"labels\":{\"en\":\"version\"},\"aliases\":[\"Version\"]},{\"name\":\"warehouse\",\"targetType\":\"Warehouse\",\"labels\":{\"en\":\"Warehouse\",\"zh-CN\":\"仓库\"},\"aliases\":[\"Warehouse\"]}]},\"Warehouse\":{\"labels\":{\"en\":\"Warehouse\",\"zh-CN\":\"仓库\"},\"fields\":[{\"name\":\"id\",\"labels\":{\"en\":\"id\"},\"aliases\":[\"Id\"]},{\"name\":\"name\",\"labels\":{\"en\":\"name\"},\"aliases\":[\"Name\"]},{\"name\":\"supplier_list\",\"targetType\":\"Supplier\",\"labels\":{\"en\":\"Supplier\",\"zh-CN\":\"供应商\"},\"aliases\":[\"SupplierList\",\"supplierList\"]},{\"name\":\"version\",\"labels\":{\"en\":\"version\"},\"aliases\":[\"Version\"]}]}}}")
GENERATED_RUNTIME_MODULE = (RuntimeModule().entity(Warehouse)
    .schema_entity(_Warehouse_DESCRIPTOR)
    .checker("Warehouse", _WarehouseChecker())
    .wire_metadata("Warehouse", create_wire_entity_metadata("Warehouse", ["id", "name", "version"], JsonFieldNamingProfile.parse("camelCase"), {"id": ["id"], "name": ["name"], "version": ["version"]})).entity(Supplier)
    .schema_entity(_Supplier_DESCRIPTOR)
    .checker("Supplier", _SupplierChecker())
    .wire_metadata("Supplier", create_wire_entity_metadata("Supplier", ["id", "warehouse", "name", "minimum_order_quantity", "version"], JsonFieldNamingProfile.parse("camelCase"), {"id": ["id"], "warehouse": ["warehouse"], "name": ["name"], "minimum_order_quantity": ["minimum_order_quantity"], "version": ["version"]}))
    .checker_presentation(_CHECKER_PRESENTATION)
    .generated_bootstrap(_ensure_generated_bootstrap)
)