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
from models.customer_order import CustomerOrder
from models.order_item import OrderItem
from models.payment import Payment
from models.payment_attempt import PaymentAttempt
from models.shipment import Shipment

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



class _CustomerOrderChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        now = context.get_resource("fix_time")
        if (operation == "insert" and "platform" not in record) or ("platform" in record and _teaql_is_null(record["platform"])):
            results.append(CheckResult("required", ObjectLocation().property("platform")))

        if (operation == "insert" and "order_number" not in record) or ("order_number" in record and _teaql_is_null(record["order_number"])):
            results.append(CheckResult("required", ObjectLocation().property("order_number")))
        if "order_number" in record and _teaql_raw(record["order_number"]) is not None and len(_teaql_raw(record["order_number"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("order_number"), _teaql_raw(record["order_number"]), 100))

        if (operation == "insert" and "description" not in record) or ("description" in record and _teaql_is_null(record["description"])):
            results.append(CheckResult("required", ObjectLocation().property("description")))
        if "description" in record and _teaql_raw(record["description"]) is not None and len(_teaql_raw(record["description"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("description"), _teaql_raw(record["description"]), 100))



class _OrderItemChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        now = context.get_resource("fix_time")
        if (operation == "insert" and "customer_order" not in record) or ("customer_order" in record and _teaql_is_null(record["customer_order"])):
            results.append(CheckResult("required", ObjectLocation().property("customer_order")))

        if (operation == "insert" and "name" not in record) or ("name" in record and _teaql_is_null(record["name"])):
            results.append(CheckResult("required", ObjectLocation().property("name")))
        if "name" in record and _teaql_raw(record["name"]) is not None and len(_teaql_raw(record["name"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("name"), _teaql_raw(record["name"]), 100))



class _PaymentChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        now = context.get_resource("fix_time")
        if (operation == "insert" and "customer_order" not in record) or ("customer_order" in record and _teaql_is_null(record["customer_order"])):
            results.append(CheckResult("required", ObjectLocation().property("customer_order")))

        if (operation == "insert" and "reference_code" not in record) or ("reference_code" in record and _teaql_is_null(record["reference_code"])):
            results.append(CheckResult("required", ObjectLocation().property("reference_code")))
        if "reference_code" in record and _teaql_raw(record["reference_code"]) is not None and len(_teaql_raw(record["reference_code"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("reference_code"), _teaql_raw(record["reference_code"]), 100))



class _PaymentAttemptChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        now = context.get_resource("fix_time")
        if (operation == "insert" and "payment" not in record) or ("payment" in record and _teaql_is_null(record["payment"])):
            results.append(CheckResult("required", ObjectLocation().property("payment")))

        if (operation == "insert" and "reference_code" not in record) or ("reference_code" in record and _teaql_is_null(record["reference_code"])):
            results.append(CheckResult("required", ObjectLocation().property("reference_code")))
        if "reference_code" in record and _teaql_raw(record["reference_code"]) is not None and len(_teaql_raw(record["reference_code"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("reference_code"), _teaql_raw(record["reference_code"]), 100))



class _ShipmentChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        now = context.get_resource("fix_time")
        if (operation == "insert" and "customer_order" not in record) or ("customer_order" in record and _teaql_is_null(record["customer_order"])):
            results.append(CheckResult("required", ObjectLocation().property("customer_order")))

        if (operation == "insert" and "reference_code" not in record) or ("reference_code" in record and _teaql_is_null(record["reference_code"])):
            results.append(CheckResult("required", ObjectLocation().property("reference_code")))
        if "reference_code" in record and _teaql_raw(record["reference_code"]) is not None and len(_teaql_raw(record["reference_code"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("reference_code"), _teaql_raw(record["reference_code"]), 100))



_Platform_DESCRIPTOR = (EntityDescriptor("Platform")
    .audit_mask_fields([])
    .table_name("platform_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("name", DataType.Text).column_name("name").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("customer_order_list", "CustomerOrder").local("id").foreign("platform").many())
)

_CustomerOrder_DESCRIPTOR = (EntityDescriptor("CustomerOrder")
    .audit_mask_fields([])
    .table_name("customer_order_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("platform", DataType.I64).column_name("platform").log_policy("plain").required()).property(PropertyDescriptor("order_number", DataType.Text).column_name("order_number").log_policy("plain").required()).property(PropertyDescriptor("description", DataType.Text).column_name("description").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("platform", "Platform").local("platform").foreign("id")).relation(RelationDescriptor("order_item_list", "OrderItem").local("id").foreign("customer_order").many()).relation(RelationDescriptor("payment_list", "Payment").local("id").foreign("customer_order").many()).relation(RelationDescriptor("shipment_list", "Shipment").local("id").foreign("customer_order").many())
)

_OrderItem_DESCRIPTOR = (EntityDescriptor("OrderItem")
    .audit_mask_fields([])
    .table_name("order_item_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("customer_order", DataType.I64).column_name("customer_order").log_policy("plain").required()).property(PropertyDescriptor("name", DataType.Text).column_name("name").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("customer_order", "CustomerOrder").local("customer_order").foreign("id"))
)

_Payment_DESCRIPTOR = (EntityDescriptor("Payment")
    .audit_mask_fields([])
    .table_name("payment_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("customer_order", DataType.I64).column_name("customer_order").log_policy("plain").required()).property(PropertyDescriptor("reference_code", DataType.Text).column_name("reference_code").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("customer_order", "CustomerOrder").local("customer_order").foreign("id")).relation(RelationDescriptor("payment_attempt_list", "PaymentAttempt").local("id").foreign("payment").many())
)

_PaymentAttempt_DESCRIPTOR = (EntityDescriptor("PaymentAttempt")
    .audit_mask_fields([])
    .table_name("payment_attempt_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("payment", DataType.I64).column_name("payment").log_policy("plain").required()).property(PropertyDescriptor("reference_code", DataType.Text).column_name("reference_code").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("payment", "Payment").local("payment").foreign("id"))
)

_Shipment_DESCRIPTOR = (EntityDescriptor("Shipment")
    .audit_mask_fields([])
    .table_name("shipment_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("customer_order", DataType.I64).column_name("customer_order").log_policy("plain").required()).property(PropertyDescriptor("reference_code", DataType.Text).column_name("reference_code").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("customer_order", "CustomerOrder").local("customer_order").foreign("id"))
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
            platform_1.update_name("Trace Chain Verification")
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
    .wire_metadata("Platform", create_wire_entity_metadata("Platform", ["id", "name", "version"], JsonFieldNamingProfile.CAMEL_CASE, {"id": ["id"], "name": ["name"], "version": ["version"]})).entity(CustomerOrder)
    .schema_entity(_CustomerOrder_DESCRIPTOR)
    .checker("CustomerOrder", _CustomerOrderChecker())
    .wire_metadata("CustomerOrder", create_wire_entity_metadata("CustomerOrder", ["id", "platform", "order_number", "description", "version"], JsonFieldNamingProfile.CAMEL_CASE, {"id": ["id"], "platform": ["platform"], "order_number": ["order_number"], "description": ["description"], "version": ["version"]})).entity(OrderItem)
    .schema_entity(_OrderItem_DESCRIPTOR)
    .checker("OrderItem", _OrderItemChecker())
    .wire_metadata("OrderItem", create_wire_entity_metadata("OrderItem", ["id", "customer_order", "name", "version"], JsonFieldNamingProfile.CAMEL_CASE, {"id": ["id"], "customer_order": ["customer_order"], "name": ["name"], "version": ["version"]})).entity(Payment)
    .schema_entity(_Payment_DESCRIPTOR)
    .checker("Payment", _PaymentChecker())
    .wire_metadata("Payment", create_wire_entity_metadata("Payment", ["id", "customer_order", "reference_code", "version"], JsonFieldNamingProfile.CAMEL_CASE, {"id": ["id"], "customer_order": ["customer_order"], "reference_code": ["reference_code"], "version": ["version"]})).entity(PaymentAttempt)
    .schema_entity(_PaymentAttempt_DESCRIPTOR)
    .checker("PaymentAttempt", _PaymentAttemptChecker())
    .wire_metadata("PaymentAttempt", create_wire_entity_metadata("PaymentAttempt", ["id", "payment", "reference_code", "version"], JsonFieldNamingProfile.CAMEL_CASE, {"id": ["id"], "payment": ["payment"], "reference_code": ["reference_code"], "version": ["version"]})).entity(Shipment)
    .schema_entity(_Shipment_DESCRIPTOR)
    .checker("Shipment", _ShipmentChecker())
    .wire_metadata("Shipment", create_wire_entity_metadata("Shipment", ["id", "customer_order", "reference_code", "version"], JsonFieldNamingProfile.CAMEL_CASE, {"id": ["id"], "customer_order": ["customer_order"], "reference_code": ["reference_code"], "version": ["version"]}))
    .generated_bootstrap(_ensure_generated_bootstrap)
)