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
from models.tenant import Tenant
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

class _TenantChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        now = context.get_resource("fix_time")
        if (operation == "insert" and "name" not in record) or ("name" in record and _teaql_is_null(record["name"])):
            results.append(CheckResult("required", ObjectLocation().property("name")))
        if "name" in record and _teaql_raw(record["name"]) is not None and not len(_teaql_raw(record["name"])) >= 1:
            results.append(CheckResult("min_length", ObjectLocation().property("name"), _teaql_raw(record["name"]), 1))
        if "name" in record and _teaql_raw(record["name"]) is not None and len(_teaql_raw(record["name"])) > 80:
            results.append(CheckResult("max_length", ObjectLocation().property("name"), _teaql_raw(record["name"]), 80))



class _PurchaseOrderChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        now = context.get_resource("fix_time")
        if operation == "insert":
            root = context.require_active_root("Tenant")
            if "tenant" in record and not _teaql_is_null(record["tenant"]):
                if _teaql_entity_id(record["tenant"]) != root.id:
                    results.append(CheckResult("context_root_mismatch", ObjectLocation().property("tenant"), _teaql_entity_id(record["tenant"]), root.id))
            else:
                record["tenant"] = Value.from_any(root.id)
                context.record_fix_evidence("PurchaseOrder", "tenant", "context", "activeRoot:Tenant")
        elif operation == "update" and "tenant" in record and not _teaql_is_null(record["tenant"]):
            root = context.require_active_root("Tenant")
            if _teaql_entity_id(record["tenant"]) != root.id:
                results.append(CheckResult("context_root_mismatch", ObjectLocation().property("tenant"), _teaql_entity_id(record["tenant"]), root.id))



        if operation == "insert" and ("create_time" not in record or _teaql_is_null(record["create_time"])):
            record["create_time"] = Value.from_any(now)
            context.record_fix_evidence("PurchaseOrder", "create_time", "clock", "graphClock")

        if operation == "insert" and ("update_time" not in record or _teaql_is_null(record["update_time"])):
            record["update_time"] = Value.from_any(now)
            context.record_fix_evidence("PurchaseOrder", "update_time", "clock", "graphClock")
        if operation == "insert" or operation == "update":
            record["update_time"] = Value.from_any(now)
            context.record_fix_evidence("PurchaseOrder", "update_time", "clock", "graphClock")


        if (operation == "insert" and "tenant" not in record) or ("tenant" in record and _teaql_is_null(record["tenant"])):
            results.append(CheckResult("required", ObjectLocation().property("tenant")))

        if (operation == "insert" and "contact_phone" not in record) or ("contact_phone" in record and _teaql_is_null(record["contact_phone"])):
            results.append(CheckResult("required", ObjectLocation().property("contact_phone")))
        if "contact_phone" in record and _teaql_raw(record["contact_phone"]) is not None and not len(_teaql_raw(record["contact_phone"])) >= 1:
            results.append(CheckResult("min_length", ObjectLocation().property("contact_phone"), _teaql_raw(record["contact_phone"]), 1))
        if "contact_phone" in record and _teaql_raw(record["contact_phone"]) is not None and len(_teaql_raw(record["contact_phone"])) > 32:
            results.append(CheckResult("max_length", ObjectLocation().property("contact_phone"), _teaql_raw(record["contact_phone"]), 32))

        if "internal_note" in record and _teaql_raw(record["internal_note"]) is not None and len(_teaql_raw(record["internal_note"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("internal_note"), _teaql_raw(record["internal_note"]), 100))

        if (operation == "insert" and "create_time" not in record) or ("create_time" in record and _teaql_is_null(record["create_time"])):
            results.append(CheckResult("required", ObjectLocation().property("create_time")))

        if (operation == "insert" and "update_time" not in record) or ("update_time" in record and _teaql_is_null(record["update_time"])):
            results.append(CheckResult("required", ObjectLocation().property("update_time")))



class _OrderItemChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        now = context.get_resource("fix_time")
        if operation == "insert":
            root = context.require_active_root("Tenant")
            if "tenant" in record and not _teaql_is_null(record["tenant"]):
                if _teaql_entity_id(record["tenant"]) != root.id:
                    results.append(CheckResult("context_root_mismatch", ObjectLocation().property("tenant"), _teaql_entity_id(record["tenant"]), root.id))
            else:
                record["tenant"] = Value.from_any(root.id)
                context.record_fix_evidence("OrderItem", "tenant", "context", "activeRoot:Tenant")
        elif operation == "update" and "tenant" in record and not _teaql_is_null(record["tenant"]):
            root = context.require_active_root("Tenant")
            if _teaql_entity_id(record["tenant"]) != root.id:
                results.append(CheckResult("context_root_mismatch", ObjectLocation().property("tenant"), _teaql_entity_id(record["tenant"]), root.id))



        if operation == "insert" and ("create_time" not in record or _teaql_is_null(record["create_time"])):
            record["create_time"] = Value.from_any(now)
            context.record_fix_evidence("OrderItem", "create_time", "clock", "graphClock")

        if operation == "insert" and ("update_time" not in record or _teaql_is_null(record["update_time"])):
            record["update_time"] = Value.from_any(now)
            context.record_fix_evidence("OrderItem", "update_time", "clock", "graphClock")
        if operation == "insert" or operation == "update":
            record["update_time"] = Value.from_any(now)
            context.record_fix_evidence("OrderItem", "update_time", "clock", "graphClock")


        if (operation == "insert" and "purchase_order" not in record) or ("purchase_order" in record and _teaql_is_null(record["purchase_order"])):
            results.append(CheckResult("required", ObjectLocation().property("purchase_order")))

        if (operation == "insert" and "tenant" not in record) or ("tenant" in record and _teaql_is_null(record["tenant"])):
            results.append(CheckResult("required", ObjectLocation().property("tenant")))

        if (operation == "insert" and "product_name" not in record) or ("product_name" in record and _teaql_is_null(record["product_name"])):
            results.append(CheckResult("required", ObjectLocation().property("product_name")))
        if "product_name" in record and _teaql_raw(record["product_name"]) is not None and not len(_teaql_raw(record["product_name"])) >= 1:
            results.append(CheckResult("min_length", ObjectLocation().property("product_name"), _teaql_raw(record["product_name"]), 1))
        if "product_name" in record and _teaql_raw(record["product_name"]) is not None and len(_teaql_raw(record["product_name"])) > 80:
            results.append(CheckResult("max_length", ObjectLocation().property("product_name"), _teaql_raw(record["product_name"]), 80))

        if (operation == "insert" and "unit_price" not in record) or ("unit_price" in record and _teaql_is_null(record["unit_price"])):
            results.append(CheckResult("required", ObjectLocation().property("unit_price")))
        if "unit_price" in record and _teaql_raw(record["unit_price"]) is not None and not _teaql_raw(record["unit_price"]) >= 0.01:
            results.append(CheckResult("min", ObjectLocation().property("unit_price"), _teaql_raw(record["unit_price"]), 0.01))
        if "unit_price" in record and _teaql_raw(record["unit_price"]) is not None and _teaql_raw(record["unit_price"]) > 1000000:
            results.append(CheckResult("max", ObjectLocation().property("unit_price"), _teaql_raw(record["unit_price"]), 1000000))

        if (operation == "insert" and "create_time" not in record) or ("create_time" in record and _teaql_is_null(record["create_time"])):
            results.append(CheckResult("required", ObjectLocation().property("create_time")))

        if (operation == "insert" and "update_time" not in record) or ("update_time" in record and _teaql_is_null(record["update_time"])):
            results.append(CheckResult("required", ObjectLocation().property("update_time")))



_Tenant_DESCRIPTOR = (EntityDescriptor("Tenant")
    .audit_mask_fields([])
    .table_name("tenant_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("name", DataType.Text).column_name("name").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("purchase_order_list", "PurchaseOrder").local("id").foreign("tenant").many()).relation(RelationDescriptor("order_item_list", "OrderItem").local("id").foreign("tenant").many())
)

_PurchaseOrder_DESCRIPTOR = (EntityDescriptor("PurchaseOrder")
    .audit_mask_fields([])
    .table_name("purchase_order_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("tenant", DataType.I64).column_name("tenant").log_policy("plain").required().fixed_by_runtime(insert=True)).property(PropertyDescriptor("contact_phone", DataType.Text).column_name("contact_phone").log_policy("plain").required()).property(PropertyDescriptor("internal_note", DataType.Text).column_name("internal_note").log_policy("plain")).property(PropertyDescriptor("create_time", DataType.Timestamp).column_name("create_time").log_policy("plain").required().fixed_by_runtime(insert=True)).property(PropertyDescriptor("update_time", DataType.Timestamp).column_name("update_time").log_policy("plain").required().fixed_by_runtime(insert=True, update=True)).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("tenant", "Tenant").local("tenant").foreign("id")).relation(RelationDescriptor("order_item_list", "OrderItem").local("id").foreign("purchase_order").many())
)

_OrderItem_DESCRIPTOR = (EntityDescriptor("OrderItem")
    .audit_mask_fields([])
    .table_name("order_item_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("purchase_order", DataType.I64).column_name("purchase_order").log_policy("plain").required()).property(PropertyDescriptor("tenant", DataType.I64).column_name("tenant").log_policy("plain").required().fixed_by_runtime(insert=True)).property(PropertyDescriptor("product_name", DataType.Text).column_name("product_name").log_policy("plain").required()).property(PropertyDescriptor("unit_price", DataType.Decimal).column_name("unit_price").log_policy("plain").required()).property(PropertyDescriptor("create_time", DataType.Timestamp).column_name("create_time").log_policy("plain").required().fixed_by_runtime(insert=True)).property(PropertyDescriptor("update_time", DataType.Timestamp).column_name("update_time").log_policy("plain").required().fixed_by_runtime(insert=True, update=True)).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("purchase_order", "PurchaseOrder").local("purchase_order").foreign("id")).relation(RelationDescriptor("tenant", "Tenant").local("tenant").foreign("id"))
)

async def _ensure_generated_bootstrap_once(context):
    previous_actor = context.user_identifier() if hasattr(context, 'user_identifier') else None
    previous_category = context.get_resource('bootstrapCategory')
    if hasattr(context, 'set_user_identifier'):
        context.set_user_identifier('teaql-generated-bootstrap')
    context.insert_resource('bootstrapCategory', 'runtime-bootstrap')
    try:
        tenant_1 = await (Q.tenants().with_id_is(1).comment('what: locate generated bootstrap entity').purpose('why: idempotent runtime bootstrap').execute_for_one(context))
        if tenant_1 is None:
            tenant_1 = Tenant._teaql_new_with_fixed_id(1)
            tenant_1.update_name("Tenant Name")
            try:
                await tenant_1.audit_as('create model root Tenant(1)').save(context)
            except Exception as _teaql_create_error:
                for _teaql_attempt in range(5):
                    tenant_1 = await (Q.tenants().with_id_is(1).comment('what: recover concurrent bootstrap').purpose('why: make generated bootstrap idempotent').execute_for_one(context))
                    if tenant_1 is not None:
                        break
                    if _teaql_attempt < 4:
                        await asyncio.sleep((_teaql_attempt + 1) * 0.01)
                if tenant_1 is None:
                    raise _teaql_create_error
        context.with_active_root(ContextEntityRef("Tenant", 1))
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
GENERATED_RUNTIME_MODULE = (RuntimeModule().entity(Tenant)
    .schema_entity(_Tenant_DESCRIPTOR)
    .checker("Tenant", _TenantChecker())
    .wire_metadata("Tenant", create_wire_entity_metadata("Tenant", ["id", "name", "version"], JsonFieldNamingProfile.CAMEL_CASE, {"id": ["id"], "name": ["name"], "version": ["version"]})).entity(PurchaseOrder)
    .schema_entity(_PurchaseOrder_DESCRIPTOR)
    .checker("PurchaseOrder", _PurchaseOrderChecker())
    .wire_metadata("PurchaseOrder", create_wire_entity_metadata("PurchaseOrder", ["id", "tenant", "contact_phone", "internal_note", "create_time", "update_time", "version"], JsonFieldNamingProfile.CAMEL_CASE, {"id": ["id"], "tenant": ["tenant"], "contact_phone": ["contact_phone"], "internal_note": ["internal_note"], "create_time": ["create_time"], "update_time": ["update_time"], "version": ["version"]})).entity(OrderItem)
    .schema_entity(_OrderItem_DESCRIPTOR)
    .checker("OrderItem", _OrderItemChecker())
    .wire_metadata("OrderItem", create_wire_entity_metadata("OrderItem", ["id", "purchase_order", "tenant", "product_name", "unit_price", "create_time", "update_time", "version"], JsonFieldNamingProfile.CAMEL_CASE, {"id": ["id"], "purchase_order": ["purchase_order"], "tenant": ["tenant"], "product_name": ["product_name"], "unit_price": ["unit_price"], "create_time": ["create_time"], "update_time": ["update_time"], "version": ["version"]}))
    .generated_bootstrap(_ensure_generated_bootstrap)
)