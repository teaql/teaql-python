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
from models.commerce_platform import CommercePlatform
from models.customer import Customer
from models.order_status import OrderStatus
from models.customer_order import CustomerOrder
from models.product import Product
from models.order_line import OrderLine
from models.order_search_preset import OrderSearchPreset

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

class _CommercePlatformChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        now = context.get_resource("fix_time")
        if operation == "insert" and ("create_time" not in record or _teaql_is_null(record["create_time"])):
            record["create_time"] = Value.from_any(now)
            context.record_fix_evidence("CommercePlatform", "create_time", "clock", "graphClock")

        if operation == "insert" and ("update_time" not in record or _teaql_is_null(record["update_time"])):
            record["update_time"] = Value.from_any(now)
            context.record_fix_evidence("CommercePlatform", "update_time", "clock", "graphClock")
        if operation == "insert" or operation == "update":
            record["update_time"] = Value.from_any(now)
            context.record_fix_evidence("CommercePlatform", "update_time", "clock", "graphClock")


        if (operation == "insert" and "name" not in record) or ("name" in record and _teaql_is_null(record["name"])):
            results.append(CheckResult("required", ObjectLocation().property("name")))
        if "name" in record and _teaql_raw(record["name"]) is not None and len(_teaql_raw(record["name"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("name"), _teaql_raw(record["name"]), 100))

        if (operation == "insert" and "create_time" not in record) or ("create_time" in record and _teaql_is_null(record["create_time"])):
            results.append(CheckResult("required", ObjectLocation().property("create_time")))

        if (operation == "insert" and "update_time" not in record) or ("update_time" in record and _teaql_is_null(record["update_time"])):
            results.append(CheckResult("required", ObjectLocation().property("update_time")))



class _CustomerChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        now = context.get_resource("fix_time")
        if operation == "insert" and ("create_time" not in record or _teaql_is_null(record["create_time"])):
            record["create_time"] = Value.from_any(now)
            context.record_fix_evidence("Customer", "create_time", "clock", "graphClock")

        if operation == "insert" and ("update_time" not in record or _teaql_is_null(record["update_time"])):
            record["update_time"] = Value.from_any(now)
            context.record_fix_evidence("Customer", "update_time", "clock", "graphClock")
        if operation == "insert" or operation == "update":
            record["update_time"] = Value.from_any(now)
            context.record_fix_evidence("Customer", "update_time", "clock", "graphClock")


        if (operation == "insert" and "name" not in record) or ("name" in record and _teaql_is_null(record["name"])):
            results.append(CheckResult("required", ObjectLocation().property("name")))
        if "name" in record and _teaql_raw(record["name"]) is not None and len(_teaql_raw(record["name"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("name"), _teaql_raw(record["name"]), 100))

        if (operation == "insert" and "email" not in record) or ("email" in record and _teaql_is_null(record["email"])):
            results.append(CheckResult("required", ObjectLocation().property("email")))
        if "email" in record and _teaql_raw(record["email"]) is not None and len(_teaql_raw(record["email"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("email"), _teaql_raw(record["email"]), 100))

        if (operation == "insert" and "commerce_platform" not in record) or ("commerce_platform" in record and _teaql_is_null(record["commerce_platform"])):
            results.append(CheckResult("required", ObjectLocation().property("commerce_platform")))

        if (operation == "insert" and "create_time" not in record) or ("create_time" in record and _teaql_is_null(record["create_time"])):
            results.append(CheckResult("required", ObjectLocation().property("create_time")))

        if (operation == "insert" and "update_time" not in record) or ("update_time" in record and _teaql_is_null(record["update_time"])):
            results.append(CheckResult("required", ObjectLocation().property("update_time")))



class _OrderStatusChecker:
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

        if "color" in record and _teaql_raw(record["color"]) is not None and len(_teaql_raw(record["color"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("color"), _teaql_raw(record["color"]), 100))


        if (operation == "insert" and "commerce_platform" not in record) or ("commerce_platform" in record and _teaql_is_null(record["commerce_platform"])):
            results.append(CheckResult("required", ObjectLocation().property("commerce_platform")))



class _CustomerOrderChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        now = context.get_resource("fix_time")
        if operation == "insert" and ("create_time" not in record or _teaql_is_null(record["create_time"])):
            record["create_time"] = Value.from_any(now)
            context.record_fix_evidence("CustomerOrder", "create_time", "clock", "graphClock")

        if operation == "insert" and ("update_time" not in record or _teaql_is_null(record["update_time"])):
            record["update_time"] = Value.from_any(now)
            context.record_fix_evidence("CustomerOrder", "update_time", "clock", "graphClock")
        if operation == "insert" or operation == "update":
            record["update_time"] = Value.from_any(now)
            context.record_fix_evidence("CustomerOrder", "update_time", "clock", "graphClock")


        if (operation == "insert" and "order_number" not in record) or ("order_number" in record and _teaql_is_null(record["order_number"])):
            results.append(CheckResult("required", ObjectLocation().property("order_number")))
        if "order_number" in record and _teaql_raw(record["order_number"]) is not None and len(_teaql_raw(record["order_number"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("order_number"), _teaql_raw(record["order_number"]), 100))

        if (operation == "insert" and "order_date" not in record) or ("order_date" in record and _teaql_is_null(record["order_date"])):
            results.append(CheckResult("required", ObjectLocation().property("order_date")))

        if (operation == "insert" and "total_amount" not in record) or ("total_amount" in record and _teaql_is_null(record["total_amount"])):
            results.append(CheckResult("required", ObjectLocation().property("total_amount")))

        if (operation == "insert" and "status" not in record) or ("status" in record and _teaql_is_null(record["status"])):
            results.append(CheckResult("required", ObjectLocation().property("status")))

        if (operation == "insert" and "customer" not in record) or ("customer" in record and _teaql_is_null(record["customer"])):
            results.append(CheckResult("required", ObjectLocation().property("customer")))

        if (operation == "insert" and "commerce_platform" not in record) or ("commerce_platform" in record and _teaql_is_null(record["commerce_platform"])):
            results.append(CheckResult("required", ObjectLocation().property("commerce_platform")))

        if (operation == "insert" and "create_time" not in record) or ("create_time" in record and _teaql_is_null(record["create_time"])):
            results.append(CheckResult("required", ObjectLocation().property("create_time")))

        if (operation == "insert" and "update_time" not in record) or ("update_time" in record and _teaql_is_null(record["update_time"])):
            results.append(CheckResult("required", ObjectLocation().property("update_time")))



class _ProductChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        now = context.get_resource("fix_time")
        if operation == "insert" and ("create_time" not in record or _teaql_is_null(record["create_time"])):
            record["create_time"] = Value.from_any(now)
            context.record_fix_evidence("Product", "create_time", "clock", "graphClock")

        if operation == "insert" and ("update_time" not in record or _teaql_is_null(record["update_time"])):
            record["update_time"] = Value.from_any(now)
            context.record_fix_evidence("Product", "update_time", "clock", "graphClock")
        if operation == "insert" or operation == "update":
            record["update_time"] = Value.from_any(now)
            context.record_fix_evidence("Product", "update_time", "clock", "graphClock")


        if (operation == "insert" and "name" not in record) or ("name" in record and _teaql_is_null(record["name"])):
            results.append(CheckResult("required", ObjectLocation().property("name")))
        if "name" in record and _teaql_raw(record["name"]) is not None and len(_teaql_raw(record["name"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("name"), _teaql_raw(record["name"]), 100))

        if (operation == "insert" and "sku" not in record) or ("sku" in record and _teaql_is_null(record["sku"])):
            results.append(CheckResult("required", ObjectLocation().property("sku")))
        if "sku" in record and _teaql_raw(record["sku"]) is not None and len(_teaql_raw(record["sku"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("sku"), _teaql_raw(record["sku"]), 100))

        if "image_url" in record and _teaql_raw(record["image_url"]) is not None and len(_teaql_raw(record["image_url"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("image_url"), _teaql_raw(record["image_url"]), 100))

        if (operation == "insert" and "commerce_platform" not in record) or ("commerce_platform" in record and _teaql_is_null(record["commerce_platform"])):
            results.append(CheckResult("required", ObjectLocation().property("commerce_platform")))

        if (operation == "insert" and "create_time" not in record) or ("create_time" in record and _teaql_is_null(record["create_time"])):
            results.append(CheckResult("required", ObjectLocation().property("create_time")))

        if (operation == "insert" and "update_time" not in record) or ("update_time" in record and _teaql_is_null(record["update_time"])):
            results.append(CheckResult("required", ObjectLocation().property("update_time")))



class _OrderLineChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        now = context.get_resource("fix_time")
        if operation == "insert" and ("create_time" not in record or _teaql_is_null(record["create_time"])):
            record["create_time"] = Value.from_any(now)
            context.record_fix_evidence("OrderLine", "create_time", "clock", "graphClock")


        if (operation == "insert" and "customer_order" not in record) or ("customer_order" in record and _teaql_is_null(record["customer_order"])):
            results.append(CheckResult("required", ObjectLocation().property("customer_order")))

        if (operation == "insert" and "product" not in record) or ("product" in record and _teaql_is_null(record["product"])):
            results.append(CheckResult("required", ObjectLocation().property("product")))

        if (operation == "insert" and "product_name" not in record) or ("product_name" in record and _teaql_is_null(record["product_name"])):
            results.append(CheckResult("required", ObjectLocation().property("product_name")))
        if "product_name" in record and _teaql_raw(record["product_name"]) is not None and len(_teaql_raw(record["product_name"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("product_name"), _teaql_raw(record["product_name"]), 100))

        if (operation == "insert" and "sku" not in record) or ("sku" in record and _teaql_is_null(record["sku"])):
            results.append(CheckResult("required", ObjectLocation().property("sku")))
        if "sku" in record and _teaql_raw(record["sku"]) is not None and len(_teaql_raw(record["sku"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("sku"), _teaql_raw(record["sku"]), 100))

        if (operation == "insert" and "quantity" not in record) or ("quantity" in record and _teaql_is_null(record["quantity"])):
            results.append(CheckResult("required", ObjectLocation().property("quantity")))

        if (operation == "insert" and "commerce_platform" not in record) or ("commerce_platform" in record and _teaql_is_null(record["commerce_platform"])):
            results.append(CheckResult("required", ObjectLocation().property("commerce_platform")))

        if (operation == "insert" and "create_time" not in record) or ("create_time" in record and _teaql_is_null(record["create_time"])):
            results.append(CheckResult("required", ObjectLocation().property("create_time")))



class _OrderSearchPresetChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        now = context.get_resource("fix_time")
        if operation == "insert" and ("create_time" not in record or _teaql_is_null(record["create_time"])):
            record["create_time"] = Value.from_any(now)
            context.record_fix_evidence("OrderSearchPreset", "create_time", "clock", "graphClock")

        if operation == "insert" and ("update_time" not in record or _teaql_is_null(record["update_time"])):
            record["update_time"] = Value.from_any(now)
            context.record_fix_evidence("OrderSearchPreset", "update_time", "clock", "graphClock")
        if operation == "insert" or operation == "update":
            record["update_time"] = Value.from_any(now)
            context.record_fix_evidence("OrderSearchPreset", "update_time", "clock", "graphClock")


        if (operation == "insert" and "name" not in record) or ("name" in record and _teaql_is_null(record["name"])):
            results.append(CheckResult("required", ObjectLocation().property("name")))
        if "name" in record and _teaql_raw(record["name"]) is not None and len(_teaql_raw(record["name"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("name"), _teaql_raw(record["name"]), 100))

        if (operation == "insert" and "filter_json" not in record) or ("filter_json" in record and _teaql_is_null(record["filter_json"])):
            results.append(CheckResult("required", ObjectLocation().property("filter_json")))
        if "filter_json" in record and _teaql_raw(record["filter_json"]) is not None and len(_teaql_raw(record["filter_json"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("filter_json"), _teaql_raw(record["filter_json"]), 100))

        if (operation == "insert" and "request_id" not in record) or ("request_id" in record and _teaql_is_null(record["request_id"])):
            results.append(CheckResult("required", ObjectLocation().property("request_id")))
        if "request_id" in record and _teaql_raw(record["request_id"]) is not None and len(_teaql_raw(record["request_id"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("request_id"), _teaql_raw(record["request_id"]), 100))

        if (operation == "insert" and "owner_user_id" not in record) or ("owner_user_id" in record and _teaql_is_null(record["owner_user_id"])):
            results.append(CheckResult("required", ObjectLocation().property("owner_user_id")))
        if "owner_user_id" in record and _teaql_raw(record["owner_user_id"]) is not None and len(_teaql_raw(record["owner_user_id"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("owner_user_id"), _teaql_raw(record["owner_user_id"]), 100))

        if (operation == "insert" and "commerce_platform" not in record) or ("commerce_platform" in record and _teaql_is_null(record["commerce_platform"])):
            results.append(CheckResult("required", ObjectLocation().property("commerce_platform")))

        if (operation == "insert" and "create_time" not in record) or ("create_time" in record and _teaql_is_null(record["create_time"])):
            results.append(CheckResult("required", ObjectLocation().property("create_time")))

        if (operation == "insert" and "update_time" not in record) or ("update_time" in record and _teaql_is_null(record["update_time"])):
            results.append(CheckResult("required", ObjectLocation().property("update_time")))



_CommercePlatform_DESCRIPTOR = (EntityDescriptor("CommercePlatform")
    .table_name("commerce_platform_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").is_id().required()).property(PropertyDescriptor("name", DataType.Text).column_name("name").required()).property(PropertyDescriptor("create_time", DataType.Timestamp).column_name("create_time").required()).property(PropertyDescriptor("update_time", DataType.Timestamp).column_name("update_time").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").is_version().required()).relation(RelationDescriptor("customer_list", "Customer").local("id").foreign("commerce_platform").many()).relation(RelationDescriptor("order_status_list", "OrderStatus").local("id").foreign("commerce_platform").many()).relation(RelationDescriptor("customer_order_list", "CustomerOrder").local("id").foreign("commerce_platform").many()).relation(RelationDescriptor("product_list", "Product").local("id").foreign("commerce_platform").many()).relation(RelationDescriptor("order_line_list", "OrderLine").local("id").foreign("commerce_platform").many()).relation(RelationDescriptor("order_search_preset_list", "OrderSearchPreset").local("id").foreign("commerce_platform").many())
)

_Customer_DESCRIPTOR = (EntityDescriptor("Customer")
    .table_name("customer_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").is_id().required()).property(PropertyDescriptor("name", DataType.Text).column_name("name").required()).property(PropertyDescriptor("email", DataType.Text).column_name("email").required()).property(PropertyDescriptor("commerce_platform", DataType.I64).column_name("commerce_platform").required()).property(PropertyDescriptor("create_time", DataType.Timestamp).column_name("create_time").required()).property(PropertyDescriptor("update_time", DataType.Timestamp).column_name("update_time").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").is_version().required()).relation(RelationDescriptor("commerce_platform", "CommercePlatform").local("commerce_platform").foreign("id")).relation(RelationDescriptor("customer_order_list", "CustomerOrder").local("id").foreign("customer").many())
)

_OrderStatus_DESCRIPTOR = (EntityDescriptor("OrderStatus")
    .table_name("order_status_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").is_id().required()).property(PropertyDescriptor("name", DataType.Text).column_name("name").required()).property(PropertyDescriptor("code", DataType.Text).column_name("code").required()).property(PropertyDescriptor("color", DataType.Text).column_name("color")).property(PropertyDescriptor("display_order", DataType.Decimal).column_name("display_order")).property(PropertyDescriptor("commerce_platform", DataType.I64).column_name("commerce_platform").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").is_version().required()).relation(RelationDescriptor("commerce_platform", "CommercePlatform").local("commerce_platform").foreign("id")).relation(RelationDescriptor("customer_order_list", "CustomerOrder").local("id").foreign("status").many())
)

_CustomerOrder_DESCRIPTOR = (EntityDescriptor("CustomerOrder")
    .table_name("customer_order_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").is_id().required()).property(PropertyDescriptor("order_number", DataType.Text).column_name("order_number").required()).property(PropertyDescriptor("order_date", DataType.Date).column_name("order_date").required()).property(PropertyDescriptor("total_amount", DataType.Decimal).column_name("total_amount").required()).property(PropertyDescriptor("status", DataType.I64).column_name("status").required()).property(PropertyDescriptor("customer", DataType.I64).column_name("customer").required()).property(PropertyDescriptor("commerce_platform", DataType.I64).column_name("commerce_platform").required()).property(PropertyDescriptor("create_time", DataType.Timestamp).column_name("create_time").required()).property(PropertyDescriptor("update_time", DataType.Timestamp).column_name("update_time").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").is_version().required()).relation(RelationDescriptor("status", "OrderStatus").local("status").foreign("id")).relation(RelationDescriptor("customer", "Customer").local("customer").foreign("id")).relation(RelationDescriptor("commerce_platform", "CommercePlatform").local("commerce_platform").foreign("id")).relation(RelationDescriptor("order_line_list", "OrderLine").local("id").foreign("customer_order").many())
)

_Product_DESCRIPTOR = (EntityDescriptor("Product")
    .table_name("product_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").is_id().required()).property(PropertyDescriptor("name", DataType.Text).column_name("name").required()).property(PropertyDescriptor("sku", DataType.Text).column_name("sku").required()).property(PropertyDescriptor("image_url", DataType.Text).column_name("image_url")).property(PropertyDescriptor("commerce_platform", DataType.I64).column_name("commerce_platform").required()).property(PropertyDescriptor("create_time", DataType.Timestamp).column_name("create_time").required()).property(PropertyDescriptor("update_time", DataType.Timestamp).column_name("update_time").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").is_version().required()).relation(RelationDescriptor("commerce_platform", "CommercePlatform").local("commerce_platform").foreign("id")).relation(RelationDescriptor("order_line_list", "OrderLine").local("id").foreign("product").many())
)

_OrderLine_DESCRIPTOR = (EntityDescriptor("OrderLine")
    .table_name("order_line_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").is_id().required()).property(PropertyDescriptor("customer_order", DataType.I64).column_name("customer_order").required()).property(PropertyDescriptor("product", DataType.I64).column_name("product").required()).property(PropertyDescriptor("product_name", DataType.Text).column_name("product_name").required()).property(PropertyDescriptor("sku", DataType.Text).column_name("sku").required()).property(PropertyDescriptor("quantity", DataType.I64).column_name("quantity").required()).property(PropertyDescriptor("commerce_platform", DataType.I64).column_name("commerce_platform").required()).property(PropertyDescriptor("create_time", DataType.Timestamp).column_name("create_time").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").is_version().required()).relation(RelationDescriptor("customer_order", "CustomerOrder").local("customer_order").foreign("id")).relation(RelationDescriptor("product", "Product").local("product").foreign("id")).relation(RelationDescriptor("commerce_platform", "CommercePlatform").local("commerce_platform").foreign("id"))
)

_OrderSearchPreset_DESCRIPTOR = (EntityDescriptor("OrderSearchPreset")
    .table_name("order_search_preset_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").is_id().required()).property(PropertyDescriptor("name", DataType.Text).column_name("name").required()).property(PropertyDescriptor("filter_json", DataType.Text).column_name("filter_json").required()).property(PropertyDescriptor("request_id", DataType.Text).column_name("request_id").required()).property(PropertyDescriptor("owner_user_id", DataType.Text).column_name("owner_user_id").required()).property(PropertyDescriptor("commerce_platform", DataType.I64).column_name("commerce_platform").required()).property(PropertyDescriptor("create_time", DataType.Timestamp).column_name("create_time").required()).property(PropertyDescriptor("update_time", DataType.Timestamp).column_name("update_time").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").is_version().required()).relation(RelationDescriptor("commerce_platform", "CommercePlatform").local("commerce_platform").foreign("id"))
)

async def _ensure_generated_bootstrap_once(context):
    previous_actor = context.user_identifier() if hasattr(context, 'user_identifier') else None
    previous_category = context.get_resource('bootstrapCategory')
    if hasattr(context, 'set_user_identifier'):
        context.set_user_identifier('teaql-generated-bootstrap')
    context.insert_resource('bootstrapCategory', 'runtime-bootstrap')
    try:
        commerce_platform_1 = await (Q.commerce_platforms().with_id_is(1).comment('what: locate generated bootstrap entity').purpose('why: idempotent runtime bootstrap').execute_for_one(context))
        if commerce_platform_1 is None:
            commerce_platform_1 = CommercePlatform._teaql_new_with_fixed_id(1)
            commerce_platform_1.update_name("Northwind Demo")
            try:
                await commerce_platform_1.audit_as('create model root CommercePlatform(1)').save(context)
            except Exception as _teaql_create_error:
                for _teaql_attempt in range(5):
                    commerce_platform_1 = await (Q.commerce_platforms().with_id_is(1).comment('what: recover concurrent bootstrap').purpose('why: make generated bootstrap idempotent').execute_for_one(context))
                    if commerce_platform_1 is not None:
                        break
                    if _teaql_attempt < 4:
                        await asyncio.sleep((_teaql_attempt + 1) * 0.01)
                if commerce_platform_1 is None:
                    raise _teaql_create_error
        context.with_active_root(ContextEntityRef("CommercePlatform", 1))
        order_status_1001 = await (Q.order_statuses().with_id_is(1001).comment('what: locate generated bootstrap entity').purpose('why: idempotent runtime bootstrap').execute_for_one(context))
        if order_status_1001 is None:
            order_status_1001 = OrderStatus._teaql_new_with_fixed_id(1001)
            order_status_1001.update_name("Pending")
            order_status_1001.update_code("PENDING")
            order_status_1001.update_color("#F59E0B")
            order_status_1001.update_display_order(1)
            order_status_1001.update_commerce_platform(CommercePlatform.refer(1))
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
        if order_status_1001.name != "Pending":
            order_status_1001.update_name("Pending")
            _teaql_changed = True
        if order_status_1001.code != "PENDING":
            order_status_1001.update_code("PENDING")
            _teaql_changed = True
        if order_status_1001.color != "#F59E0B":
            order_status_1001.update_color("#F59E0B")
            _teaql_changed = True
        if order_status_1001.displayOrder != 1:
            order_status_1001.update_display_order(1)
            _teaql_changed = True
        if order_status_1001.commercePlatform != 1:
            order_status_1001.update_commerce_platform(CommercePlatform.refer(1))
            _teaql_changed = True
        if _teaql_changed:
            await order_status_1001.audit_as('reconcile model constant OrderStatus(1001)').save(context)
        order_status_1002 = await (Q.order_statuses().with_id_is(1002).comment('what: locate generated bootstrap entity').purpose('why: idempotent runtime bootstrap').execute_for_one(context))
        if order_status_1002 is None:
            order_status_1002 = OrderStatus._teaql_new_with_fixed_id(1002)
            order_status_1002.update_name("Confirmed")
            order_status_1002.update_code("CONFIRMED")
            order_status_1002.update_color("#10B981")
            order_status_1002.update_display_order(2)
            order_status_1002.update_commerce_platform(CommercePlatform.refer(1))
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
        if order_status_1002.name != "Confirmed":
            order_status_1002.update_name("Confirmed")
            _teaql_changed = True
        if order_status_1002.code != "CONFIRMED":
            order_status_1002.update_code("CONFIRMED")
            _teaql_changed = True
        if order_status_1002.color != "#10B981":
            order_status_1002.update_color("#10B981")
            _teaql_changed = True
        if order_status_1002.displayOrder != 2:
            order_status_1002.update_display_order(2)
            _teaql_changed = True
        if order_status_1002.commercePlatform != 1:
            order_status_1002.update_commerce_platform(CommercePlatform.refer(1))
            _teaql_changed = True
        if _teaql_changed:
            await order_status_1002.audit_as('reconcile model constant OrderStatus(1002)').save(context)
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
GENERATED_RUNTIME_MODULE = (RuntimeModule().entity(CommercePlatform)
    .schema_entity(_CommercePlatform_DESCRIPTOR)
    .checker("CommercePlatform", _CommercePlatformChecker())
    .wire_metadata("CommercePlatform", create_wire_entity_metadata("CommercePlatform", ["id", "name", "create_time", "update_time", "version"], JsonFieldNamingProfile.CAMEL_CASE, {"id": ["id"], "name": ["name"], "create_time": ["create_time"], "update_time": ["update_time"], "version": ["version"]})).entity(Customer)
    .schema_entity(_Customer_DESCRIPTOR)
    .checker("Customer", _CustomerChecker())
    .wire_metadata("Customer", create_wire_entity_metadata("Customer", ["id", "name", "email", "commerce_platform", "create_time", "update_time", "version"], JsonFieldNamingProfile.CAMEL_CASE, {"id": ["id"], "name": ["name"], "email": ["email"], "commerce_platform": ["commerce_platform"], "create_time": ["create_time"], "update_time": ["update_time"], "version": ["version"]})).entity(OrderStatus)
    .schema_entity(_OrderStatus_DESCRIPTOR)
    .checker("OrderStatus", _OrderStatusChecker())
    .wire_metadata("OrderStatus", create_wire_entity_metadata("OrderStatus", ["id", "name", "code", "color", "display_order", "commerce_platform", "version"], JsonFieldNamingProfile.CAMEL_CASE, {"id": ["id"], "name": ["name"], "code": ["code"], "color": ["color"], "display_order": ["display_order"], "commerce_platform": ["commerce_platform"], "version": ["version"]})).entity(CustomerOrder)
    .schema_entity(_CustomerOrder_DESCRIPTOR)
    .checker("CustomerOrder", _CustomerOrderChecker())
    .wire_metadata("CustomerOrder", create_wire_entity_metadata("CustomerOrder", ["id", "order_number", "order_date", "total_amount", "status", "customer", "commerce_platform", "create_time", "update_time", "version"], JsonFieldNamingProfile.CAMEL_CASE, {"id": ["id"], "order_number": ["order_number"], "order_date": ["order_date"], "total_amount": ["total_amount"], "status": ["status"], "customer": ["customer"], "commerce_platform": ["commerce_platform"], "create_time": ["create_time"], "update_time": ["update_time"], "version": ["version"]})).entity(Product)
    .schema_entity(_Product_DESCRIPTOR)
    .checker("Product", _ProductChecker())
    .wire_metadata("Product", create_wire_entity_metadata("Product", ["id", "name", "sku", "image_url", "commerce_platform", "create_time", "update_time", "version"], JsonFieldNamingProfile.CAMEL_CASE, {"id": ["id"], "name": ["name"], "sku": ["sku"], "image_url": ["image_url"], "commerce_platform": ["commerce_platform"], "create_time": ["create_time"], "update_time": ["update_time"], "version": ["version"]})).entity(OrderLine)
    .schema_entity(_OrderLine_DESCRIPTOR)
    .checker("OrderLine", _OrderLineChecker())
    .wire_metadata("OrderLine", create_wire_entity_metadata("OrderLine", ["id", "customer_order", "product", "product_name", "sku", "quantity", "commerce_platform", "create_time", "version"], JsonFieldNamingProfile.CAMEL_CASE, {"id": ["id"], "customer_order": ["customer_order"], "product": ["product"], "product_name": ["product_name"], "sku": ["sku"], "quantity": ["quantity"], "commerce_platform": ["commerce_platform"], "create_time": ["create_time"], "version": ["version"]})).entity(OrderSearchPreset)
    .schema_entity(_OrderSearchPreset_DESCRIPTOR)
    .checker("OrderSearchPreset", _OrderSearchPresetChecker())
    .wire_metadata("OrderSearchPreset", create_wire_entity_metadata("OrderSearchPreset", ["id", "name", "filter_json", "request_id", "owner_user_id", "commerce_platform", "create_time", "update_time", "version"], JsonFieldNamingProfile.CAMEL_CASE, {"id": ["id"], "name": ["name"], "filter_json": ["filter_json"], "request_id": ["request_id"], "owner_user_id": ["owner_user_id"], "commerce_platform": ["commerce_platform"], "create_time": ["create_time"], "update_time": ["update_time"], "version": ["version"]}))
    .generated_bootstrap(_ensure_generated_bootstrap)
)