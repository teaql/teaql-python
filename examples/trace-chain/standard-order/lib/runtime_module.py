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
from models.order_status import OrderStatus
from models.customer import Customer
from models.customer_order import CustomerOrder
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

class _PlatformChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        now = context.get_resource("fix_time")
        if (operation == "insert" and "name" not in record) or ("name" in record and _teaql_is_null(record["name"])):
            results.append(CheckResult("required", ObjectLocation().property("name")))
        if "name" in record and _teaql_raw(record["name"]) is not None and len(_teaql_raw(record["name"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("name"), _teaql_raw(record["name"]), 100))



class _OrderStatusChecker:
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

        if (operation == "insert" and "color" not in record) or ("color" in record and _teaql_is_null(record["color"])):
            results.append(CheckResult("required", ObjectLocation().property("color")))
        if "color" in record and _teaql_raw(record["color"]) is not None and len(_teaql_raw(record["color"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("color"), _teaql_raw(record["color"]), 100))

        if (operation == "insert" and "display_order" not in record) or ("display_order" in record and _teaql_is_null(record["display_order"])):
            results.append(CheckResult("required", ObjectLocation().property("display_order")))



class _CustomerChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        now = context.get_resource("fix_time")
        if (operation == "insert" and "platform" not in record) or ("platform" in record and _teaql_is_null(record["platform"])):
            results.append(CheckResult("required", ObjectLocation().property("platform")))

        if (operation == "insert" and "name" not in record) or ("name" in record and _teaql_is_null(record["name"])):
            results.append(CheckResult("required", ObjectLocation().property("name")))
        if "name" in record and _teaql_raw(record["name"]) is not None and len(_teaql_raw(record["name"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("name"), _teaql_raw(record["name"]), 100))



class _CustomerOrderChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        now = context.get_resource("fix_time")
        if (operation == "insert" and "customer" not in record) or ("customer" in record and _teaql_is_null(record["customer"])):
            results.append(CheckResult("required", ObjectLocation().property("customer")))

        if (operation == "insert" and "status" not in record) or ("status" in record and _teaql_is_null(record["status"])):
            results.append(CheckResult("required", ObjectLocation().property("status")))

        if (operation == "insert" and "order_number" not in record) or ("order_number" in record and _teaql_is_null(record["order_number"])):
            results.append(CheckResult("required", ObjectLocation().property("order_number")))
        if "order_number" in record and _teaql_raw(record["order_number"]) is not None and len(_teaql_raw(record["order_number"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("order_number"), _teaql_raw(record["order_number"]), 100))

        if (operation == "insert" and "order_date" not in record) or ("order_date" in record and _teaql_is_null(record["order_date"])):
            results.append(CheckResult("required", ObjectLocation().property("order_date")))

        if (operation == "insert" and "total_amount" not in record) or ("total_amount" in record and _teaql_is_null(record["total_amount"])):
            results.append(CheckResult("required", ObjectLocation().property("total_amount")))



class _OrderItemChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        now = context.get_resource("fix_time")
        if (operation == "insert" and "customer_order" not in record) or ("customer_order" in record and _teaql_is_null(record["customer_order"])):
            results.append(CheckResult("required", ObjectLocation().property("customer_order")))

        if (operation == "insert" and "product_name" not in record) or ("product_name" in record and _teaql_is_null(record["product_name"])):
            results.append(CheckResult("required", ObjectLocation().property("product_name")))
        if "product_name" in record and _teaql_raw(record["product_name"]) is not None and len(_teaql_raw(record["product_name"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("product_name"), _teaql_raw(record["product_name"]), 100))

        if (operation == "insert" and "quantity" not in record) or ("quantity" in record and _teaql_is_null(record["quantity"])):
            results.append(CheckResult("required", ObjectLocation().property("quantity")))

        if (operation == "insert" and "unit_price" not in record) or ("unit_price" in record and _teaql_is_null(record["unit_price"])):
            results.append(CheckResult("required", ObjectLocation().property("unit_price")))



_Platform_DESCRIPTOR = (EntityDescriptor("Platform")
    .audit_mask_fields([])
    .table_name("platform_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("name", DataType.Text).column_name("name").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("order_status_list", "OrderStatus").local("id").foreign("platform").many()).relation(RelationDescriptor("customer_list", "Customer").local("id").foreign("platform").many())
)

_OrderStatus_DESCRIPTOR = (EntityDescriptor("OrderStatus")
    .audit_mask_fields([])
    .table_name("order_status_data").property(PropertyDescriptor("platform", DataType.I64).column_name("platform").log_policy("plain").required()).property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("name", DataType.Text).column_name("name").log_policy("plain").required()).property(PropertyDescriptor("code", DataType.Text).column_name("code").log_policy("plain").required()).property(PropertyDescriptor("color", DataType.Text).column_name("color").log_policy("plain").required()).property(PropertyDescriptor("display_order", DataType.I64).column_name("display_order").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("platform", "Platform").local("platform").foreign("id")).relation(RelationDescriptor("customer_order_list", "CustomerOrder").local("id").foreign("status").many())
)

_Customer_DESCRIPTOR = (EntityDescriptor("Customer")
    .audit_mask_fields([])
    .table_name("customer_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("platform", DataType.I64).column_name("platform").log_policy("plain").required()).property(PropertyDescriptor("name", DataType.Text).column_name("name").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("platform", "Platform").local("platform").foreign("id")).relation(RelationDescriptor("customer_order_list", "CustomerOrder").local("id").foreign("customer").many())
)

_CustomerOrder_DESCRIPTOR = (EntityDescriptor("CustomerOrder")
    .audit_mask_fields([])
    .table_name("customer_order_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("customer", DataType.I64).column_name("customer").log_policy("plain").required()).property(PropertyDescriptor("status", DataType.I64).column_name("status").log_policy("plain").required()).property(PropertyDescriptor("order_number", DataType.Text).column_name("order_number").log_policy("plain").required()).property(PropertyDescriptor("order_date", DataType.Date).column_name("order_date").log_policy("plain").required()).property(PropertyDescriptor("total_amount", DataType.Decimal).column_name("total_amount").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("customer", "Customer").local("customer").foreign("id")).relation(RelationDescriptor("status", "OrderStatus").local("status").foreign("id")).relation(RelationDescriptor("order_item_list", "OrderItem").local("id").foreign("customer_order").many())
)

_OrderItem_DESCRIPTOR = (EntityDescriptor("OrderItem")
    .audit_mask_fields([])
    .table_name("order_item_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("customer_order", DataType.I64).column_name("customer_order").log_policy("plain").required()).property(PropertyDescriptor("product_name", DataType.Text).column_name("product_name").log_policy("plain").required()).property(PropertyDescriptor("quantity", DataType.I64).column_name("quantity").log_policy("plain").required()).property(PropertyDescriptor("unit_price", DataType.Decimal).column_name("unit_price").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("customer_order", "CustomerOrder").local("customer_order").foreign("id"))
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
            platform_1.update_name("Commerce Test Platform")
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
        order_status_1001 = await (Q.order_statuses().with_id_is(1001).comment('what: locate generated bootstrap entity').purpose('why: idempotent runtime bootstrap').execute_for_one(context))
        if order_status_1001 is None:
            order_status_1001 = OrderStatus._teaql_new_with_fixed_id(1001)
            order_status_1001.update_platform(Platform.refer(1))
            order_status_1001.update_name("New")
            order_status_1001.update_code("NEW")
            order_status_1001.update_color("#94A3B8")
            order_status_1001.update_display_order(1)
            try:
                await order_status_1001.audit_as('create model constant OrderStatus(1001)').save(context)
            except Exception as _teaql_create_error:
                for _teaql_attempt in range(5):
                    order_status_1001 = await (Q.order_statuses().with_id_is(1001).comment('what: recover concurrent bootstrap').purpose('why: make generated bootstrap idempotent').execute_for_one(context))
                    if order_status_1001 is not None:
                        break
                    if _teaql_attempt < 4:
                        await asyncio.sleep((_teaql_attempt + 1) * 0.01)
                if order_status_1001 is None:
                    raise _teaql_create_error
        _teaql_changed = False
        if order_status_1001.platform != 1:
            order_status_1001.update_platform(Platform.refer(1))
            _teaql_changed = True
        if order_status_1001.name != "New":
            order_status_1001.update_name("New")
            _teaql_changed = True
        if order_status_1001.code != "NEW":
            order_status_1001.update_code("NEW")
            _teaql_changed = True
        if order_status_1001.color != "#94A3B8":
            order_status_1001.update_color("#94A3B8")
            _teaql_changed = True
        if order_status_1001.displayOrder != 1:
            order_status_1001.update_display_order(1)
            _teaql_changed = True
        if _teaql_changed:
            await order_status_1001.audit_as('reconcile model constant OrderStatus(1001)').save(context)
        order_status_1002 = await (Q.order_statuses().with_id_is(1002).comment('what: locate generated bootstrap entity').purpose('why: idempotent runtime bootstrap').execute_for_one(context))
        if order_status_1002 is None:
            order_status_1002 = OrderStatus._teaql_new_with_fixed_id(1002)
            order_status_1002.update_platform(Platform.refer(1))
            order_status_1002.update_name("Paid")
            order_status_1002.update_code("PAID")
            order_status_1002.update_color("#22C55E")
            order_status_1002.update_display_order(2)
            try:
                await order_status_1002.audit_as('create model constant OrderStatus(1002)').save(context)
            except Exception as _teaql_create_error:
                for _teaql_attempt in range(5):
                    order_status_1002 = await (Q.order_statuses().with_id_is(1002).comment('what: recover concurrent bootstrap').purpose('why: make generated bootstrap idempotent').execute_for_one(context))
                    if order_status_1002 is not None:
                        break
                    if _teaql_attempt < 4:
                        await asyncio.sleep((_teaql_attempt + 1) * 0.01)
                if order_status_1002 is None:
                    raise _teaql_create_error
        _teaql_changed = False
        if order_status_1002.platform != 1:
            order_status_1002.update_platform(Platform.refer(1))
            _teaql_changed = True
        if order_status_1002.name != "Paid":
            order_status_1002.update_name("Paid")
            _teaql_changed = True
        if order_status_1002.code != "PAID":
            order_status_1002.update_code("PAID")
            _teaql_changed = True
        if order_status_1002.color != "#22C55E":
            order_status_1002.update_color("#22C55E")
            _teaql_changed = True
        if order_status_1002.displayOrder != 2:
            order_status_1002.update_display_order(2)
            _teaql_changed = True
        if _teaql_changed:
            await order_status_1002.audit_as('reconcile model constant OrderStatus(1002)').save(context)
        order_status_1003 = await (Q.order_statuses().with_id_is(1003).comment('what: locate generated bootstrap entity').purpose('why: idempotent runtime bootstrap').execute_for_one(context))
        if order_status_1003 is None:
            order_status_1003 = OrderStatus._teaql_new_with_fixed_id(1003)
            order_status_1003.update_platform(Platform.refer(1))
            order_status_1003.update_name("Cancelled")
            order_status_1003.update_code("CANCELLED")
            order_status_1003.update_color("#EF4444")
            order_status_1003.update_display_order(3)
            try:
                await order_status_1003.audit_as('create model constant OrderStatus(1003)').save(context)
            except Exception as _teaql_create_error:
                for _teaql_attempt in range(5):
                    order_status_1003 = await (Q.order_statuses().with_id_is(1003).comment('what: recover concurrent bootstrap').purpose('why: make generated bootstrap idempotent').execute_for_one(context))
                    if order_status_1003 is not None:
                        break
                    if _teaql_attempt < 4:
                        await asyncio.sleep((_teaql_attempt + 1) * 0.01)
                if order_status_1003 is None:
                    raise _teaql_create_error
        _teaql_changed = False
        if order_status_1003.platform != 1:
            order_status_1003.update_platform(Platform.refer(1))
            _teaql_changed = True
        if order_status_1003.name != "Cancelled":
            order_status_1003.update_name("Cancelled")
            _teaql_changed = True
        if order_status_1003.code != "CANCELLED":
            order_status_1003.update_code("CANCELLED")
            _teaql_changed = True
        if order_status_1003.color != "#EF4444":
            order_status_1003.update_color("#EF4444")
            _teaql_changed = True
        if order_status_1003.displayOrder != 3:
            order_status_1003.update_display_order(3)
            _teaql_changed = True
        if _teaql_changed:
            await order_status_1003.audit_as('reconcile model constant OrderStatus(1003)').save(context)
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
    .wire_metadata("Platform", create_wire_entity_metadata("Platform", ["id", "name", "version"], JsonFieldNamingProfile.CAMEL_CASE, {"id": ["id"], "name": ["name"], "version": ["version"]})).entity(OrderStatus)
    .schema_entity(_OrderStatus_DESCRIPTOR)
    .checker("OrderStatus", _OrderStatusChecker())
    .wire_metadata("OrderStatus", create_wire_entity_metadata("OrderStatus", ["platform", "id", "name", "code", "color", "display_order", "version"], JsonFieldNamingProfile.CAMEL_CASE, {"platform": ["platform"], "id": ["id"], "name": ["name"], "code": ["code"], "color": ["color"], "display_order": ["display_order"], "version": ["version"]})).entity(Customer)
    .schema_entity(_Customer_DESCRIPTOR)
    .checker("Customer", _CustomerChecker())
    .wire_metadata("Customer", create_wire_entity_metadata("Customer", ["id", "platform", "name", "version"], JsonFieldNamingProfile.CAMEL_CASE, {"id": ["id"], "platform": ["platform"], "name": ["name"], "version": ["version"]})).entity(CustomerOrder)
    .schema_entity(_CustomerOrder_DESCRIPTOR)
    .checker("CustomerOrder", _CustomerOrderChecker())
    .wire_metadata("CustomerOrder", create_wire_entity_metadata("CustomerOrder", ["id", "customer", "status", "order_number", "order_date", "total_amount", "version"], JsonFieldNamingProfile.CAMEL_CASE, {"id": ["id"], "customer": ["customer"], "status": ["status"], "order_number": ["order_number"], "order_date": ["order_date"], "total_amount": ["total_amount"], "version": ["version"]})).entity(OrderItem)
    .schema_entity(_OrderItem_DESCRIPTOR)
    .checker("OrderItem", _OrderItemChecker())
    .wire_metadata("OrderItem", create_wire_entity_metadata("OrderItem", ["id", "customer_order", "product_name", "quantity", "unit_price", "version"], JsonFieldNamingProfile.CAMEL_CASE, {"id": ["id"], "customer_order": ["customer_order"], "product_name": ["product_name"], "quantity": ["quantity"], "unit_price": ["unit_price"], "version": ["version"]}))
    .generated_bootstrap(_ensure_generated_bootstrap)
)