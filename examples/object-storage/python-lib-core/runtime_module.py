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
from models.commerce_platform import CommercePlatform
from models.customer_order import CustomerOrder
from models.order_attachment import OrderAttachment

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
        if (operation == "insert" and "name" not in record) or ("name" in record and _teaql_is_null(record["name"])):
            results.append(CheckResult("required", ObjectLocation().property("name")))
        if "name" in record and _teaql_raw(record["name"]) is not None and len(_teaql_raw(record["name"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("name"), _teaql_raw(record["name"]), 100))



class _CustomerOrderChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        if (operation == "insert" and "order_number" not in record) or ("order_number" in record and _teaql_is_null(record["order_number"])):
            results.append(CheckResult("required", ObjectLocation().property("order_number")))
        if "order_number" in record and _teaql_raw(record["order_number"]) is not None and len(_teaql_raw(record["order_number"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("order_number"), _teaql_raw(record["order_number"]), 100))

        if (operation == "insert" and "commerce_platform" not in record) or ("commerce_platform" in record and _teaql_is_null(record["commerce_platform"])):
            results.append(CheckResult("required", ObjectLocation().property("commerce_platform")))



class _OrderAttachmentChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        if (operation == "insert" and "customer_order" not in record) or ("customer_order" in record and _teaql_is_null(record["customer_order"])):
            results.append(CheckResult("required", ObjectLocation().property("customer_order")))

        if (operation == "insert" and "file_name" not in record) or ("file_name" in record and _teaql_is_null(record["file_name"])):
            results.append(CheckResult("required", ObjectLocation().property("file_name")))
        if "file_name" in record and _teaql_raw(record["file_name"]) is not None and len(_teaql_raw(record["file_name"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("file_name"), _teaql_raw(record["file_name"]), 100))

        if (operation == "insert" and "content_type" not in record) or ("content_type" in record and _teaql_is_null(record["content_type"])):
            results.append(CheckResult("required", ObjectLocation().property("content_type")))
        if "content_type" in record and _teaql_raw(record["content_type"]) is not None and len(_teaql_raw(record["content_type"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("content_type"), _teaql_raw(record["content_type"]), 100))

        if (operation == "insert" and "content_length" not in record) or ("content_length" in record and _teaql_is_null(record["content_length"])):
            results.append(CheckResult("required", ObjectLocation().property("content_length")))

        if (operation == "insert" and "content_sha256" not in record) or ("content_sha256" in record and _teaql_is_null(record["content_sha256"])):
            results.append(CheckResult("required", ObjectLocation().property("content_sha256")))
        if "content_sha256" in record and _teaql_raw(record["content_sha256"]) is not None and len(_teaql_raw(record["content_sha256"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("content_sha256"), _teaql_raw(record["content_sha256"]), 100))

        if (operation == "insert" and "object_key" not in record) or ("object_key" in record and _teaql_is_null(record["object_key"])):
            results.append(CheckResult("required", ObjectLocation().property("object_key")))
        if "object_key" in record and _teaql_raw(record["object_key"]) is not None and len(_teaql_raw(record["object_key"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("object_key"), _teaql_raw(record["object_key"]), 100))



_CommercePlatform_DESCRIPTOR = (EntityDescriptor("CommercePlatform")
    .audit_mask_fields([])
    .table_name("commerce_platform_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("name", DataType.Text).column_name("name").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("customer_order_list", "CustomerOrder").local("id").foreign("commerce_platform").many())
)

_CustomerOrder_DESCRIPTOR = (EntityDescriptor("CustomerOrder")
    .audit_mask_fields([])
    .table_name("customer_order_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("order_number", DataType.Text).column_name("order_number").log_policy("plain").required()).property(PropertyDescriptor("commerce_platform", DataType.I64).column_name("commerce_platform").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("commerce_platform", "CommercePlatform").local("commerce_platform").foreign("id")).relation(RelationDescriptor("order_attachment_list", "OrderAttachment").local("id").foreign("customer_order").many())
)

_OrderAttachment_DESCRIPTOR = (EntityDescriptor("OrderAttachment")
    .audit_mask_fields(["object_key"])
    .table_name("order_attachment_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("customer_order", DataType.I64).column_name("customer_order").log_policy("plain").required()).property(PropertyDescriptor("file_name", DataType.Text).column_name("file_name").log_policy("plain").required()).property(PropertyDescriptor("content_type", DataType.Text).column_name("content_type").log_policy("plain").required()).property(PropertyDescriptor("content_length", DataType.I64).column_name("content_length").log_policy("plain").integer32().required()).property(PropertyDescriptor("content_sha256", DataType.Text).column_name("content_sha256").log_policy("plain").required()).property(PropertyDescriptor("object_key", DataType.Text).column_name("object_key").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("customer_order", "CustomerOrder").local("customer_order").foreign("id"))
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
            commerce_platform_1 = await Q.commerce_platforms().comment('reserve generated bootstrap identity').purpose('create a managed bootstrap entity').new_entity(context)
            commerce_platform_1.update_id(1)
            commerce_platform_1.update_name("Order Attachments")
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
_CHECKER_PRESENTATION = CheckerPresentationModel.from_json("{\"schema\":\"teaql.checker-model/v1\",\"revision\":\"sha256:f6fb4b9ca6d876325850fdce5a0d2ab5c57f19c74af6bbffb2b494779e9c27b9\",\"entities\":{\"CommercePlatform\":{\"labels\":{\"en\":\"commerce platform\"},\"fields\":[{\"name\":\"customer_order_list\",\"targetType\":\"CustomerOrder\",\"labels\":{\"en\":\"customer order\"},\"aliases\":[\"CustomerOrderList\",\"customerOrderList\"]},{\"name\":\"id\",\"labels\":{\"en\":\"id\"},\"aliases\":[\"Id\"]},{\"name\":\"name\",\"labels\":{\"en\":\"name\"},\"aliases\":[\"Name\"]},{\"name\":\"version\",\"labels\":{\"en\":\"version\"},\"aliases\":[\"Version\"]}]},\"CustomerOrder\":{\"labels\":{\"en\":\"customer order\"},\"fields\":[{\"name\":\"commerce_platform\",\"targetType\":\"CommercePlatform\",\"labels\":{\"en\":\"commerce platform\"},\"aliases\":[\"CommercePlatform\",\"commercePlatform\"]},{\"name\":\"id\",\"labels\":{\"en\":\"id\"},\"aliases\":[\"Id\"]},{\"name\":\"order_attachment_list\",\"targetType\":\"OrderAttachment\",\"labels\":{\"en\":\"order attachment\"},\"aliases\":[\"OrderAttachmentList\",\"orderAttachmentList\"]},{\"name\":\"order_number\",\"labels\":{\"en\":\"order number\"},\"aliases\":[\"OrderNumber\",\"orderNumber\"]},{\"name\":\"version\",\"labels\":{\"en\":\"version\"},\"aliases\":[\"Version\"]}]},\"OrderAttachment\":{\"labels\":{\"en\":\"order attachment\"},\"fields\":[{\"name\":\"content_length\",\"labels\":{\"en\":\"content length\"},\"aliases\":[\"ContentLength\",\"contentLength\"]},{\"name\":\"content_sha256\",\"labels\":{\"en\":\"content sha256\"},\"aliases\":[\"ContentSha256\",\"contentSha256\"]},{\"name\":\"content_type\",\"labels\":{\"en\":\"content type\"},\"aliases\":[\"ContentType\",\"contentType\"]},{\"name\":\"customer_order\",\"targetType\":\"CustomerOrder\",\"labels\":{\"en\":\"customer order\"},\"aliases\":[\"CustomerOrder\",\"customerOrder\"]},{\"name\":\"file_name\",\"labels\":{\"en\":\"file name\"},\"aliases\":[\"FileName\",\"fileName\"]},{\"name\":\"id\",\"labels\":{\"en\":\"id\"},\"aliases\":[\"Id\"]},{\"name\":\"object_key\",\"labels\":{\"en\":\"object key\"},\"aliases\":[\"ObjectKey\",\"objectKey\"]},{\"name\":\"version\",\"labels\":{\"en\":\"version\"},\"aliases\":[\"Version\"]}]}}}")
GENERATED_RUNTIME_MODULE = (RuntimeModule().entity(CommercePlatform)
    .schema_entity(_CommercePlatform_DESCRIPTOR)
    .checker("CommercePlatform", _CommercePlatformChecker())
    .wire_metadata("CommercePlatform", create_wire_entity_metadata("CommercePlatform", ["id", "name", "version"], JsonFieldNamingProfile.parse("camelCase"), {"id": ["id"], "name": ["name"], "version": ["version"]})).entity(CustomerOrder)
    .schema_entity(_CustomerOrder_DESCRIPTOR)
    .checker("CustomerOrder", _CustomerOrderChecker())
    .wire_metadata("CustomerOrder", create_wire_entity_metadata("CustomerOrder", ["id", "order_number", "commerce_platform", "version"], JsonFieldNamingProfile.parse("camelCase"), {"id": ["id"], "order_number": ["order_number"], "commerce_platform": ["commerce_platform"], "version": ["version"]})).entity(OrderAttachment)
    .schema_entity(_OrderAttachment_DESCRIPTOR)
    .checker("OrderAttachment", _OrderAttachmentChecker())
    .wire_metadata("OrderAttachment", create_wire_entity_metadata("OrderAttachment", ["id", "customer_order", "file_name", "content_type", "content_length", "content_sha256", "object_key", "version"], JsonFieldNamingProfile.parse("camelCase"), {"id": ["id"], "customer_order": ["customer_order"], "file_name": ["file_name"], "content_type": ["content_type"], "content_length": ["content_length"], "content_sha256": ["content_sha256"], "object_key": ["object_key"], "version": ["version"]}))
    .checker_presentation(_CHECKER_PRESENTATION)
    .generated_bootstrap(_ensure_generated_bootstrap)
)