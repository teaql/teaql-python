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
from models.customer import Customer
from models.customer_contact import CustomerContact

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



class _CustomerChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        if (operation == "insert" and "platform" not in record) or ("platform" in record and _teaql_is_null(record["platform"])):
            results.append(CheckResult("required", ObjectLocation().property("platform")))

        if (operation == "insert" and "email" not in record) or ("email" in record and _teaql_is_null(record["email"])):
            results.append(CheckResult("required", ObjectLocation().property("email")))
        if "email" in record and _teaql_raw(record["email"]) is not None and not len(_teaql_raw(record["email"])) >= 1:
            results.append(CheckResult("min_length", ObjectLocation().property("email"), _teaql_raw(record["email"]), 1))
        if "email" in record and _teaql_raw(record["email"]) is not None and len(_teaql_raw(record["email"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("email"), _teaql_raw(record["email"]), 100))



class _CustomerContactChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        if (operation == "insert" and "customer" not in record) or ("customer" in record and _teaql_is_null(record["customer"])):
            results.append(CheckResult("required", ObjectLocation().property("customer")))

        if (operation == "insert" and "channel" not in record) or ("channel" in record and _teaql_is_null(record["channel"])):
            results.append(CheckResult("required", ObjectLocation().property("channel")))
        if "channel" in record and _teaql_raw(record["channel"]) is not None and not len(_teaql_raw(record["channel"])) >= 1:
            results.append(CheckResult("min_length", ObjectLocation().property("channel"), _teaql_raw(record["channel"]), 1))
        if "channel" in record and _teaql_raw(record["channel"]) is not None and len(_teaql_raw(record["channel"])) > 40:
            results.append(CheckResult("max_length", ObjectLocation().property("channel"), _teaql_raw(record["channel"]), 40))



_Platform_DESCRIPTOR = (EntityDescriptor("Platform")
    .audit_mask_fields([])
    .table_name("platform_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("name", DataType.Text).column_name("name").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("customer_list", "Customer").local("id").foreign("platform").many())
)

_Customer_DESCRIPTOR = (EntityDescriptor("Customer")
    .audit_mask_fields([])
    .table_name("customer_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("platform", DataType.I64).column_name("platform").log_policy("plain").required()).property(PropertyDescriptor("email", DataType.Text).column_name("email").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("platform", "Platform").local("platform").foreign("id")).relation(RelationDescriptor("customer_contact_list", "CustomerContact").local("id").foreign("customer").many())
)

_CustomerContact_DESCRIPTOR = (EntityDescriptor("CustomerContact")
    .audit_mask_fields([])
    .table_name("customer_contact_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("customer", DataType.I64).column_name("customer").log_policy("plain").required()).property(PropertyDescriptor("channel", DataType.Text).column_name("channel").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("customer", "Customer").local("customer").foreign("id"))
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
            platform_1.update_name("Customer Services")
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
_CHECKER_PRESENTATION = CheckerPresentationModel.from_json("{\"schema\":\"teaql.checker-model/v1\",\"revision\":\"sha256:c4dce4f2f6d12ed07cc3f68d59eebf08de6689664fb11cc4e7621965517d9763\",\"entities\":{\"Customer\":{\"labels\":{\"en\":\"customer\"},\"fields\":[{\"name\":\"customer_contact_list\",\"targetType\":\"CustomerContact\",\"labels\":{\"en\":\"customer contact\"},\"aliases\":[\"CustomerContactList\",\"customerContactList\"]},{\"name\":\"email\",\"labels\":{\"en\":\"email\"},\"aliases\":[\"Email\"]},{\"name\":\"id\",\"labels\":{\"en\":\"id\"},\"aliases\":[\"Id\"]},{\"name\":\"platform\",\"targetType\":\"Platform\",\"labels\":{\"en\":\"platform\"},\"aliases\":[\"Platform\"]},{\"name\":\"version\",\"labels\":{\"en\":\"version\"},\"aliases\":[\"Version\"]}]},\"CustomerContact\":{\"labels\":{\"en\":\"customer contact\"},\"fields\":[{\"name\":\"channel\",\"labels\":{\"en\":\"channel\"},\"aliases\":[\"Channel\"]},{\"name\":\"customer\",\"targetType\":\"Customer\",\"labels\":{\"en\":\"customer\"},\"aliases\":[\"Customer\"]},{\"name\":\"id\",\"labels\":{\"en\":\"id\"},\"aliases\":[\"Id\"]},{\"name\":\"version\",\"labels\":{\"en\":\"version\"},\"aliases\":[\"Version\"]}]},\"Platform\":{\"labels\":{\"en\":\"platform\"},\"fields\":[{\"name\":\"customer_list\",\"targetType\":\"Customer\",\"labels\":{\"en\":\"customer\"},\"aliases\":[\"CustomerList\",\"customerList\"]},{\"name\":\"id\",\"labels\":{\"en\":\"id\"},\"aliases\":[\"Id\"]},{\"name\":\"name\",\"labels\":{\"en\":\"name\"},\"aliases\":[\"Name\"]},{\"name\":\"version\",\"labels\":{\"en\":\"version\"},\"aliases\":[\"Version\"]}]}}}")
GENERATED_RUNTIME_MODULE = (RuntimeModule().entity(Platform)
    .schema_entity(_Platform_DESCRIPTOR)
    .checker("Platform", _PlatformChecker())
    .wire_metadata("Platform", create_wire_entity_metadata("Platform", ["id", "name", "version"], JsonFieldNamingProfile.parse("camelCase"), {"id": ["id"], "name": ["name"], "version": ["version"]})).entity(Customer)
    .schema_entity(_Customer_DESCRIPTOR)
    .checker("Customer", _CustomerChecker())
    .wire_metadata("Customer", create_wire_entity_metadata("Customer", ["id", "platform", "email", "version"], JsonFieldNamingProfile.parse("camelCase"), {"id": ["id"], "platform": ["platform"], "email": ["email"], "version": ["version"]})).entity(CustomerContact)
    .schema_entity(_CustomerContact_DESCRIPTOR)
    .checker("CustomerContact", _CustomerContactChecker())
    .wire_metadata("CustomerContact", create_wire_entity_metadata("CustomerContact", ["id", "customer", "channel", "version"], JsonFieldNamingProfile.parse("camelCase"), {"id": ["id"], "customer": ["customer"], "channel": ["channel"], "version": ["version"]}))
    .checker_presentation(_CHECKER_PRESENTATION)
    .generated_bootstrap(_ensure_generated_bootstrap)
)