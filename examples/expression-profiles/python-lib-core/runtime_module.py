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
from models.distribution_center import DistributionCenter
from models.dispatch_order import DispatchOrder

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

class _DistributionCenterChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        if (operation == "insert" and "dock_name" not in record) or ("dock_name" in record and _teaql_is_null(record["dock_name"])):
            results.append(CheckResult("required", ObjectLocation().property("dock_name")))
        if "dock_name" in record and _teaql_raw(record["dock_name"]) is not None and len(_teaql_raw(record["dock_name"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("dock_name"), _teaql_raw(record["dock_name"]), 100))



class _DispatchOrderChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        if (operation == "insert" and "distribution_center" not in record) or ("distribution_center" in record and _teaql_is_null(record["distribution_center"])):
            results.append(CheckResult("required", ObjectLocation().property("distribution_center")))

        if (operation == "insert" and "order_reference" not in record) or ("order_reference" in record and _teaql_is_null(record["order_reference"])):
            results.append(CheckResult("required", ObjectLocation().property("order_reference")))
        if "order_reference" in record and _teaql_raw(record["order_reference"]) is not None and len(_teaql_raw(record["order_reference"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("order_reference"), _teaql_raw(record["order_reference"]), 100))

        if (operation == "insert" and "handling_note" not in record) or ("handling_note" in record and _teaql_is_null(record["handling_note"])):
            results.append(CheckResult("required", ObjectLocation().property("handling_note")))
        if "handling_note" in record and _teaql_raw(record["handling_note"]) is not None and len(_teaql_raw(record["handling_note"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("handling_note"), _teaql_raw(record["handling_note"]), 100))



_DistributionCenter_DESCRIPTOR = (EntityDescriptor("DistributionCenter")
    .audit_mask_fields([])
    .table_name("distribution_center_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("dock_name", DataType.Text).column_name("dock_name").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("dispatch_order_list", "DispatchOrder").local("id").foreign("distribution_center").many())
)

_DispatchOrder_DESCRIPTOR = (EntityDescriptor("DispatchOrder")
    .audit_mask_fields([])
    .table_name("dispatch_order_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("distribution_center", DataType.I64).column_name("distribution_center").log_policy("plain").required()).property(PropertyDescriptor("order_reference", DataType.Text).column_name("order_reference").log_policy("plain").required()).property(PropertyDescriptor("handling_note", DataType.Text).column_name("handling_note").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("distribution_center", "DistributionCenter").local("distribution_center").foreign("id"))
)

async def _ensure_generated_bootstrap_once(context):
    previous_actor = context.user_identifier() if hasattr(context, 'user_identifier') else None
    previous_category = context.get_resource('bootstrapCategory')
    if hasattr(context, 'set_user_identifier'):
        context.set_user_identifier('teaql-generated-bootstrap')
    context.insert_resource('bootstrapCategory', 'runtime-bootstrap')
    try:
        distribution_center_1 = await (Q.distribution_centers().with_id_is(1).comment('what: locate generated bootstrap entity').purpose('why: idempotent runtime bootstrap').execute_for_one(context))
        if distribution_center_1 is None:
            distribution_center_1 = await Q.distribution_centers().comment('reserve generated bootstrap identity').purpose('create a managed bootstrap entity').new_entity(context)
            distribution_center_1.update_id(1)
            distribution_center_1.update_dock_name("North Receiving Terminal")
            try:
                await distribution_center_1.audit_as('create model root DistributionCenter(1)').save(context)
            except Exception as _teaql_create_error:
                for _teaql_attempt in range(5):
                    distribution_center_1 = await (Q.distribution_centers().with_id_is(1).comment('what: recover concurrent bootstrap').purpose('why: make generated bootstrap idempotent').execute_for_one(context))
                    if distribution_center_1 is not None:
                        break
                    if _teaql_attempt < 4:
                        await asyncio.sleep((_teaql_attempt + 1) * 0.01)
                if distribution_center_1 is None:
                    raise _teaql_create_error
        context.with_active_root(ContextEntityRef("DistributionCenter", 1))
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
_CHECKER_PRESENTATION = CheckerPresentationModel.from_json("{\"schema\":\"teaql.checker-model/v1\",\"revision\":\"sha256:77ad1b3df638005c05c3bca45d54d613c2443bb125585299b8cdcd3593870eae\",\"entities\":{\"DispatchOrder\":{\"labels\":{\"en\":\"dispatch order\"},\"fields\":[{\"name\":\"distribution_center\",\"targetType\":\"DistributionCenter\",\"labels\":{\"en\":\"distribution center\"},\"aliases\":[\"DistributionCenter\",\"distributionCenter\"]},{\"name\":\"handling_note\",\"labels\":{\"en\":\"handling note\"},\"aliases\":[\"HandlingNote\",\"handlingNote\"]},{\"name\":\"id\",\"labels\":{\"en\":\"id\"},\"aliases\":[\"Id\"]},{\"name\":\"order_reference\",\"labels\":{\"en\":\"order reference\"},\"aliases\":[\"OrderReference\",\"orderReference\"]},{\"name\":\"version\",\"labels\":{\"en\":\"version\"},\"aliases\":[\"Version\"]}]},\"DistributionCenter\":{\"labels\":{\"en\":\"distribution center\"},\"fields\":[{\"name\":\"dispatch_order_list\",\"targetType\":\"DispatchOrder\",\"labels\":{\"en\":\"dispatch order\"},\"aliases\":[\"DispatchOrderList\",\"dispatchOrderList\"]},{\"name\":\"dock_name\",\"labels\":{\"en\":\"dock name\"},\"aliases\":[\"DockName\",\"dockName\"]},{\"name\":\"id\",\"labels\":{\"en\":\"id\"},\"aliases\":[\"Id\"]},{\"name\":\"version\",\"labels\":{\"en\":\"version\"},\"aliases\":[\"Version\"]}]}}}")
GENERATED_RUNTIME_MODULE = (RuntimeModule().entity(DistributionCenter)
    .schema_entity(_DistributionCenter_DESCRIPTOR)
    .checker("DistributionCenter", _DistributionCenterChecker())
    .wire_metadata("DistributionCenter", create_wire_entity_metadata("DistributionCenter", ["id", "dock_name", "version"], JsonFieldNamingProfile.parse("camelCase"), {"id": ["id"], "dock_name": ["dock_name"], "version": ["version"]})).entity(DispatchOrder)
    .schema_entity(_DispatchOrder_DESCRIPTOR)
    .checker("DispatchOrder", _DispatchOrderChecker())
    .wire_metadata("DispatchOrder", create_wire_entity_metadata("DispatchOrder", ["id", "distribution_center", "order_reference", "handling_note", "version"], JsonFieldNamingProfile.parse("camelCase"), {"id": ["id"], "distribution_center": ["distribution_center"], "order_reference": ["order_reference"], "handling_note": ["handling_note"], "version": ["version"]}))
    .checker_presentation(_CHECKER_PRESENTATION)
    .generated_bootstrap(_ensure_generated_bootstrap)
)