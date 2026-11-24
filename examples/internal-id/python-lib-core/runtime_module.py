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
from models.purchase_order import PurchaseOrder
from models.order_item import OrderItem

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



class _PurchaseOrderChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        if (operation == "insert" and "warehouse" not in record) or ("warehouse" in record and _teaql_is_null(record["warehouse"])):
            results.append(CheckResult("required", ObjectLocation().property("warehouse")))

        if (operation == "insert" and "reference" not in record) or ("reference" in record and _teaql_is_null(record["reference"])):
            results.append(CheckResult("required", ObjectLocation().property("reference")))
        if "reference" in record and _teaql_raw(record["reference"]) is not None and len(_teaql_raw(record["reference"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("reference"), _teaql_raw(record["reference"]), 100))



class _OrderItemChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        if (operation == "insert" and "purchase_order" not in record) or ("purchase_order" in record and _teaql_is_null(record["purchase_order"])):
            results.append(CheckResult("required", ObjectLocation().property("purchase_order")))

        if (operation == "insert" and "sku" not in record) or ("sku" in record and _teaql_is_null(record["sku"])):
            results.append(CheckResult("required", ObjectLocation().property("sku")))
        if "sku" in record and _teaql_raw(record["sku"]) is not None and len(_teaql_raw(record["sku"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("sku"), _teaql_raw(record["sku"]), 100))

        if (operation == "insert" and "quantity" not in record) or ("quantity" in record and _teaql_is_null(record["quantity"])):
            results.append(CheckResult("required", ObjectLocation().property("quantity")))



_Warehouse_DESCRIPTOR = (EntityDescriptor("Warehouse")
    .audit_mask_fields([])
    .table_name("warehouse_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("name", DataType.Text).column_name("name").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("purchase_order_list", "PurchaseOrder").local("id").foreign("warehouse").many())
)

_PurchaseOrder_DESCRIPTOR = (EntityDescriptor("PurchaseOrder")
    .audit_mask_fields([])
    .table_name("purchase_order_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("warehouse", DataType.I64).column_name("warehouse").log_policy("plain").required()).property(PropertyDescriptor("reference", DataType.Text).column_name("reference").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("warehouse", "Warehouse").local("warehouse").foreign("id")).relation(RelationDescriptor("order_item_list", "OrderItem").local("id").foreign("purchase_order").many())
)

_OrderItem_DESCRIPTOR = (EntityDescriptor("OrderItem")
    .audit_mask_fields([])
    .table_name("order_item_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("purchase_order", DataType.I64).column_name("purchase_order").log_policy("plain").required()).property(PropertyDescriptor("sku", DataType.Text).column_name("sku").log_policy("plain").required()).property(PropertyDescriptor("quantity", DataType.I64).column_name("quantity").log_policy("plain").integer32().required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("purchase_order", "PurchaseOrder").local("purchase_order").foreign("id"))
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
            warehouse_1 = await Q.warehouses().comment('reserve generated bootstrap identity').purpose('create a managed bootstrap entity').new_entity(context)
            warehouse_1.update_id(1)
            warehouse_1.update_name("Riverside Distribution Center")
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
_CHECKER_PRESENTATION = CheckerPresentationModel.from_json("{\"schema\":\"teaql.checker-model/v1\",\"revision\":\"sha256:46dda51da34ae53bdd51c3f7b44a0ce6ab6e8f26ca7c04a16160397cee58c3d4\",\"entities\":{\"OrderItem\":{\"labels\":{\"en\":\"Order Item\"},\"fields\":[{\"name\":\"id\",\"labels\":{\"en\":\"id\"},\"aliases\":[\"Id\"]},{\"name\":\"purchase_order\",\"targetType\":\"PurchaseOrder\",\"labels\":{\"en\":\"Purchase Order\"},\"aliases\":[\"PurchaseOrder\",\"purchaseOrder\"]},{\"name\":\"quantity\",\"labels\":{\"en\":\"quantity\"},\"aliases\":[\"Quantity\"]},{\"name\":\"sku\",\"labels\":{\"en\":\"sku\"},\"aliases\":[\"Sku\"]},{\"name\":\"version\",\"labels\":{\"en\":\"version\"},\"aliases\":[\"Version\"]}]},\"PurchaseOrder\":{\"labels\":{\"en\":\"Purchase Order\"},\"fields\":[{\"name\":\"id\",\"labels\":{\"en\":\"id\"},\"aliases\":[\"Id\"]},{\"name\":\"order_item_list\",\"targetType\":\"OrderItem\",\"labels\":{\"en\":\"Order Item\"},\"aliases\":[\"OrderItemList\",\"orderItemList\"]},{\"name\":\"reference\",\"labels\":{\"en\":\"reference\"},\"aliases\":[\"Reference\"]},{\"name\":\"version\",\"labels\":{\"en\":\"version\"},\"aliases\":[\"Version\"]},{\"name\":\"warehouse\",\"targetType\":\"Warehouse\",\"labels\":{\"en\":\"Warehouse\"},\"aliases\":[\"Warehouse\"]}]},\"Warehouse\":{\"labels\":{\"en\":\"Warehouse\"},\"fields\":[{\"name\":\"id\",\"labels\":{\"en\":\"id\"},\"aliases\":[\"Id\"]},{\"name\":\"name\",\"labels\":{\"en\":\"name\"},\"aliases\":[\"Name\"]},{\"name\":\"purchase_order_list\",\"targetType\":\"PurchaseOrder\",\"labels\":{\"en\":\"Purchase Order\"},\"aliases\":[\"PurchaseOrderList\",\"purchaseOrderList\"]},{\"name\":\"version\",\"labels\":{\"en\":\"version\"},\"aliases\":[\"Version\"]}]}}}")
GENERATED_RUNTIME_MODULE = (RuntimeModule().entity(Warehouse)
    .schema_entity(_Warehouse_DESCRIPTOR)
    .checker("Warehouse", _WarehouseChecker())
    .wire_metadata("Warehouse", create_wire_entity_metadata("Warehouse", ["id", "name", "version"], JsonFieldNamingProfile.parse("camelCase"), {"id": ["id"], "name": ["name"], "version": ["version"]})).entity(PurchaseOrder)
    .schema_entity(_PurchaseOrder_DESCRIPTOR)
    .checker("PurchaseOrder", _PurchaseOrderChecker())
    .wire_metadata("PurchaseOrder", create_wire_entity_metadata("PurchaseOrder", ["id", "warehouse", "reference", "version"], JsonFieldNamingProfile.parse("camelCase"), {"id": ["id"], "warehouse": ["warehouse"], "reference": ["reference"], "version": ["version"]})).entity(OrderItem)
    .schema_entity(_OrderItem_DESCRIPTOR)
    .checker("OrderItem", _OrderItemChecker())
    .wire_metadata("OrderItem", create_wire_entity_metadata("OrderItem", ["id", "purchase_order", "sku", "quantity", "version"], JsonFieldNamingProfile.parse("camelCase"), {"id": ["id"], "purchase_order": ["purchase_order"], "sku": ["sku"], "quantity": ["quantity"], "version": ["version"]}))
    .checker_presentation(_CHECKER_PRESENTATION)
    .generated_bootstrap(_ensure_generated_bootstrap)
)