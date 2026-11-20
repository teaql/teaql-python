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
from models.platform import Platform
from models.freight_quote import FreightQuote

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



class _FreightQuoteChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        if (operation == "insert" and "platform" not in record) or ("platform" in record and _teaql_is_null(record["platform"])):
            results.append(CheckResult("required", ObjectLocation().property("platform")))

        if (operation == "insert" and "reference" not in record) or ("reference" in record and _teaql_is_null(record["reference"])):
            results.append(CheckResult("required", ObjectLocation().property("reference")))
        if "reference" in record and _teaql_raw(record["reference"]) is not None and len(_teaql_raw(record["reference"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("reference"), _teaql_raw(record["reference"]), 100))

        if (operation == "insert" and "amount" not in record) or ("amount" in record and _teaql_is_null(record["amount"])):
            results.append(CheckResult("required", ObjectLocation().property("amount")))

        if (operation == "insert" and "shipment_number" not in record) or ("shipment_number" in record and _teaql_is_null(record["shipment_number"])):
            results.append(CheckResult("required", ObjectLocation().property("shipment_number")))

        if (operation == "insert" and "package_count" not in record) or ("package_count" in record and _teaql_is_null(record["package_count"])):
            results.append(CheckResult("required", ObjectLocation().property("package_count")))

        if (operation == "insert" and "delivery_date" not in record) or ("delivery_date" in record and _teaql_is_null(record["delivery_date"])):
            results.append(CheckResult("required", ObjectLocation().property("delivery_date")))

        if (operation == "insert" and "pickup_time" not in record) or ("pickup_time" in record and _teaql_is_null(record["pickup_time"])):
            results.append(CheckResult("required", ObjectLocation().property("pickup_time")))

        if (operation == "insert" and "quoted_at" not in record) or ("quoted_at" in record and _teaql_is_null(record["quoted_at"])):
            results.append(CheckResult("required", ObjectLocation().property("quoted_at")))

        if "instructions" in record and _teaql_raw(record["instructions"]) is not None and len(_teaql_raw(record["instructions"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("instructions"), _teaql_raw(record["instructions"]), 100))



_Platform_DESCRIPTOR = (EntityDescriptor("Platform")
    .audit_mask_fields([])
    .table_name("platform_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("name", DataType.Text).column_name("name").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("freight_quote_list", "FreightQuote").local("id").foreign("platform").many())
)

_FreightQuote_DESCRIPTOR = (EntityDescriptor("FreightQuote")
    .audit_mask_fields([])
    .table_name("freight_quote_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("platform", DataType.I64).column_name("platform").log_policy("plain").required()).property(PropertyDescriptor("reference", DataType.Text).column_name("reference").log_policy("plain").required()).property(PropertyDescriptor("amount", DataType.Decimal).column_name("amount").log_policy("plain").required()).property(PropertyDescriptor("shipment_number", DataType.I64).column_name("shipment_number").log_policy("plain").required()).property(PropertyDescriptor("package_count", DataType.I64).column_name("package_count").log_policy("plain").integer32().required()).property(PropertyDescriptor("delivery_date", DataType.Date).column_name("delivery_date").log_policy("plain").required()).property(PropertyDescriptor("pickup_time", DataType.Time).column_name("pickup_time").log_policy("plain").required()).property(PropertyDescriptor("quoted_at", DataType.Timestamp).column_name("quoted_at").log_policy("plain").required()).property(PropertyDescriptor("instructions", DataType.Text).column_name("instructions").log_policy("plain")).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("platform", "Platform").local("platform").foreign("id"))
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
            platform_1.update_name("Harbor Freight Desk")
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
_CHECKER_PRESENTATION = CheckerPresentationModel.from_json("{\"schema\":\"teaql.checker-model/v1\",\"revision\":\"sha256:3b8da34e762562f0877bfd04865e33c225b4d854c8a5914ea30b4a922d3df3b7\",\"entities\":{\"FreightQuote\":{\"labels\":{\"en\":\"Freight Quote\"},\"fields\":[{\"name\":\"amount\",\"labels\":{\"en\":\"amount\"},\"aliases\":[\"Amount\"]},{\"name\":\"delivery_date\",\"labels\":{\"en\":\"delivery date\"},\"aliases\":[\"DeliveryDate\",\"deliveryDate\"]},{\"name\":\"id\",\"labels\":{\"en\":\"id\"},\"aliases\":[\"Id\"]},{\"name\":\"instructions\",\"labels\":{\"en\":\"instructions\"},\"aliases\":[\"Instructions\"]},{\"name\":\"package_count\",\"labels\":{\"en\":\"package count\"},\"aliases\":[\"PackageCount\",\"packageCount\"]},{\"name\":\"pickup_time\",\"labels\":{\"en\":\"pickup time\"},\"aliases\":[\"PickupTime\",\"pickupTime\"]},{\"name\":\"platform\",\"targetType\":\"Platform\",\"labels\":{\"en\":\"Dispatch Platform\"},\"aliases\":[\"Platform\"]},{\"name\":\"quoted_at\",\"labels\":{\"en\":\"quoted at\"},\"aliases\":[\"QuotedAt\",\"quotedAt\"]},{\"name\":\"reference\",\"labels\":{\"en\":\"reference\"},\"aliases\":[\"Reference\"]},{\"name\":\"shipment_number\",\"labels\":{\"en\":\"shipment number\"},\"aliases\":[\"ShipmentNumber\",\"shipmentNumber\"]},{\"name\":\"version\",\"labels\":{\"en\":\"version\"},\"aliases\":[\"Version\"]}]},\"Platform\":{\"labels\":{\"en\":\"Dispatch Platform\"},\"fields\":[{\"name\":\"freight_quote_list\",\"targetType\":\"FreightQuote\",\"labels\":{\"en\":\"Freight Quote\"},\"aliases\":[\"FreightQuoteList\",\"freightQuoteList\"]},{\"name\":\"id\",\"labels\":{\"en\":\"id\"},\"aliases\":[\"Id\"]},{\"name\":\"name\",\"labels\":{\"en\":\"name\"},\"aliases\":[\"Name\"]},{\"name\":\"version\",\"labels\":{\"en\":\"version\"},\"aliases\":[\"Version\"]}]}}}")
GENERATED_RUNTIME_MODULE = (RuntimeModule().entity(Platform)
    .schema_entity(_Platform_DESCRIPTOR)
    .checker("Platform", _PlatformChecker())
    .wire_metadata("Platform", create_wire_entity_metadata("Platform", ["id", "name", "version"], JsonFieldNamingProfile.parse("camelCase"), {"id": ["id"], "name": ["name"], "version": ["version"]})).entity(FreightQuote)
    .schema_entity(_FreightQuote_DESCRIPTOR)
    .checker("FreightQuote", _FreightQuoteChecker())
    .wire_metadata("FreightQuote", create_wire_entity_metadata("FreightQuote", ["id", "platform", "reference", "amount", "shipment_number", "package_count", "delivery_date", "pickup_time", "quoted_at", "instructions", "version"], JsonFieldNamingProfile.parse("camelCase"), {"id": ["id"], "platform": ["platform"], "reference": ["reference"], "amount": ["amount"], "shipment_number": ["shipment_number"], "package_count": ["package_count"], "delivery_date": ["delivery_date"], "pickup_time": ["pickup_time"], "quoted_at": ["quoted_at"], "instructions": ["instructions"], "version": ["version"]}))
    .checker_presentation(_CHECKER_PRESENTATION)
    .generated_bootstrap(_ensure_generated_bootstrap)
)