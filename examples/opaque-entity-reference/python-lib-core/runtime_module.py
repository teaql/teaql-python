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
from models.merchant import Merchant
from models.sales_order import SalesOrder
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

class _MerchantChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        if (operation == "insert" and "name" not in record) or ("name" in record and _teaql_is_null(record["name"])):
            results.append(CheckResult("required", ObjectLocation().property("name")))
        if "name" in record and _teaql_raw(record["name"]) is not None and len(_teaql_raw(record["name"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("name"), _teaql_raw(record["name"]), 100))



class _SalesOrderChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        if (operation == "insert" and "merchant" not in record) or ("merchant" in record and _teaql_is_null(record["merchant"])):
            results.append(CheckResult("required", ObjectLocation().property("merchant")))

        if (operation == "insert" and "order_number" not in record) or ("order_number" in record and _teaql_is_null(record["order_number"])):
            results.append(CheckResult("required", ObjectLocation().property("order_number")))
        if "order_number" in record and _teaql_raw(record["order_number"]) is not None and len(_teaql_raw(record["order_number"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("order_number"), _teaql_raw(record["order_number"]), 100))



class _OrderItemChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        if (operation == "insert" and "sales_order" not in record) or ("sales_order" in record and _teaql_is_null(record["sales_order"])):
            results.append(CheckResult("required", ObjectLocation().property("sales_order")))

        if (operation == "insert" and "sku" not in record) or ("sku" in record and _teaql_is_null(record["sku"])):
            results.append(CheckResult("required", ObjectLocation().property("sku")))
        if "sku" in record and _teaql_raw(record["sku"]) is not None and len(_teaql_raw(record["sku"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("sku"), _teaql_raw(record["sku"]), 100))

        if (operation == "insert" and "quantity" not in record) or ("quantity" in record and _teaql_is_null(record["quantity"])):
            results.append(CheckResult("required", ObjectLocation().property("quantity")))



_Merchant_DESCRIPTOR = (EntityDescriptor("Merchant")
    .audit_mask_fields([])
    .table_name("merchant_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("name", DataType.Text).column_name("name").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("sales_order_list", "SalesOrder").local("id").foreign("merchant").many())
)

_SalesOrder_DESCRIPTOR = (EntityDescriptor("SalesOrder")
    .audit_mask_fields([])
    .table_name("sales_order_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("merchant", DataType.I64).column_name("merchant").log_policy("plain").required()).property(PropertyDescriptor("order_number", DataType.Text).column_name("order_number").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("merchant", "Merchant").local("merchant").foreign("id")).relation(RelationDescriptor("order_item_list", "OrderItem").local("id").foreign("sales_order").many())
)

_OrderItem_DESCRIPTOR = (EntityDescriptor("OrderItem")
    .audit_mask_fields([])
    .table_name("order_item_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("sales_order", DataType.I64).column_name("sales_order").log_policy("plain").required()).property(PropertyDescriptor("sku", DataType.Text).column_name("sku").log_policy("plain").required()).property(PropertyDescriptor("quantity", DataType.I64).column_name("quantity").log_policy("plain").integer32().required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("sales_order", "SalesOrder").local("sales_order").foreign("id"))
)

async def _ensure_generated_bootstrap_once(context):
    previous_actor = context.user_identifier() if hasattr(context, 'user_identifier') else None
    previous_category = context.get_resource('bootstrapCategory')
    if hasattr(context, 'set_user_identifier'):
        context.set_user_identifier('teaql-generated-bootstrap')
    context.insert_resource('bootstrapCategory', 'runtime-bootstrap')
    try:
        merchant_1 = await (Q.merchants().with_id_is(1).comment('what: locate generated bootstrap entity').purpose('why: idempotent runtime bootstrap').execute_for_one(context))
        if merchant_1 is None:
            merchant_1 = await Q.merchants().comment('reserve generated bootstrap identity').purpose('create a managed bootstrap entity').new_entity(context)
            merchant_1.update_id(1)
            merchant_1.update_name("Northwind Retail")
            try:
                await merchant_1.audit_as('create model root Merchant(1)').save(context)
            except Exception as _teaql_create_error:
                for _teaql_attempt in range(5):
                    merchant_1 = await (Q.merchants().with_id_is(1).comment('what: recover concurrent bootstrap').purpose('why: make generated bootstrap idempotent').execute_for_one(context))
                    if merchant_1 is not None:
                        break
                    if _teaql_attempt < 4:
                        await asyncio.sleep((_teaql_attempt + 1) * 0.01)
                if merchant_1 is None:
                    raise _teaql_create_error
        context.with_active_root(ContextEntityRef("Merchant", 1))
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
_CHECKER_PRESENTATION = CheckerPresentationModel.from_json("{\"schema\":\"teaql.checker-model/v1\",\"revision\":\"sha256:c2dacaf8377a726fc38a9cf13920679bb314d4127c7cc9c550dc98d516508240\",\"entities\":{\"Merchant\":{\"labels\":{\"en\":\"merchant\"},\"fields\":[{\"name\":\"id\",\"labels\":{\"en\":\"id\"},\"aliases\":[\"Id\"]},{\"name\":\"name\",\"labels\":{\"en\":\"name\"},\"aliases\":[\"Name\"]},{\"name\":\"sales_order_list\",\"targetType\":\"SalesOrder\",\"labels\":{\"en\":\"sales order\"},\"aliases\":[\"SalesOrderList\",\"salesOrderList\"]},{\"name\":\"version\",\"labels\":{\"en\":\"version\"},\"aliases\":[\"Version\"]}]},\"OrderItem\":{\"labels\":{\"en\":\"order item\"},\"fields\":[{\"name\":\"id\",\"labels\":{\"en\":\"id\"},\"aliases\":[\"Id\"]},{\"name\":\"quantity\",\"labels\":{\"en\":\"quantity\"},\"aliases\":[\"Quantity\"]},{\"name\":\"sales_order\",\"targetType\":\"SalesOrder\",\"labels\":{\"en\":\"sales order\"},\"aliases\":[\"SalesOrder\",\"salesOrder\"]},{\"name\":\"sku\",\"labels\":{\"en\":\"sku\"},\"aliases\":[\"Sku\"]},{\"name\":\"version\",\"labels\":{\"en\":\"version\"},\"aliases\":[\"Version\"]}]},\"SalesOrder\":{\"labels\":{\"en\":\"sales order\"},\"fields\":[{\"name\":\"id\",\"labels\":{\"en\":\"id\"},\"aliases\":[\"Id\"]},{\"name\":\"merchant\",\"targetType\":\"Merchant\",\"labels\":{\"en\":\"merchant\"},\"aliases\":[\"Merchant\"]},{\"name\":\"order_item_list\",\"targetType\":\"OrderItem\",\"labels\":{\"en\":\"order item\"},\"aliases\":[\"OrderItemList\",\"orderItemList\"]},{\"name\":\"order_number\",\"labels\":{\"en\":\"order number\"},\"aliases\":[\"OrderNumber\",\"orderNumber\"]},{\"name\":\"version\",\"labels\":{\"en\":\"version\"},\"aliases\":[\"Version\"]}]}}}")
GENERATED_RUNTIME_MODULE = (RuntimeModule().entity(Merchant)
    .schema_entity(_Merchant_DESCRIPTOR)
    .checker("Merchant", _MerchantChecker())
    .wire_metadata("Merchant", create_wire_entity_metadata("Merchant", ["id", "name", "version"], JsonFieldNamingProfile.parse("camelCase"), {"id": ["id"], "name": ["name"], "version": ["version"]})).entity(SalesOrder)
    .schema_entity(_SalesOrder_DESCRIPTOR)
    .checker("SalesOrder", _SalesOrderChecker())
    .wire_metadata("SalesOrder", create_wire_entity_metadata("SalesOrder", ["id", "merchant", "order_number", "version"], JsonFieldNamingProfile.parse("camelCase"), {"id": ["id"], "merchant": ["merchant"], "order_number": ["order_number"], "version": ["version"]})).entity(OrderItem)
    .schema_entity(_OrderItem_DESCRIPTOR)
    .checker("OrderItem", _OrderItemChecker())
    .wire_metadata("OrderItem", create_wire_entity_metadata("OrderItem", ["id", "sales_order", "sku", "quantity", "version"], JsonFieldNamingProfile.parse("camelCase"), {"id": ["id"], "sales_order": ["sales_order"], "sku": ["sku"], "quantity": ["quantity"], "version": ["version"]}))
    .checker_presentation(_CHECKER_PRESENTATION)
    .generated_bootstrap(_ensure_generated_bootstrap)
)