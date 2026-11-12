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
from models.catalog import Catalog
from models.entry import Entry

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

class _CatalogChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        if (operation == "insert" and "name" not in record) or ("name" in record and _teaql_is_null(record["name"])):
            results.append(CheckResult("required", ObjectLocation().property("name")))
        if "name" in record and _teaql_raw(record["name"]) is not None and len(_teaql_raw(record["name"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("name"), _teaql_raw(record["name"]), 100))



class _EntryChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        if operation == "insert":
            ContextFix.apply(context, record, "born_at", "now", [], location_name="born_at")

        if operation == "insert":
            ContextFix.apply(context, record, "touched_at", "now", [], location_name="touched_at")
        if operation == "update":
            ContextFix.apply(context, record, "touched_at", "now", [], location_name="touched_at")


        if (operation == "insert" and "catalog" not in record) or ("catalog" in record and _teaql_is_null(record["catalog"])):
            results.append(CheckResult("required", ObjectLocation().property("catalog")))

        if (operation == "insert" and "name" not in record) or ("name" in record and _teaql_is_null(record["name"])):
            results.append(CheckResult("required", ObjectLocation().property("name")))
        if "name" in record and _teaql_raw(record["name"]) is not None and len(_teaql_raw(record["name"])) > 100:
            results.append(CheckResult("max_length", ObjectLocation().property("name"), _teaql_raw(record["name"]), 100))

        if (operation == "insert" and "born_at" not in record) or ("born_at" in record and _teaql_is_null(record["born_at"])):
            results.append(CheckResult("required", ObjectLocation().property("born_at")))

        if (operation == "insert" and "touched_at" not in record) or ("touched_at" in record and _teaql_is_null(record["touched_at"])):
            results.append(CheckResult("required", ObjectLocation().property("touched_at")))



_Catalog_DESCRIPTOR = (EntityDescriptor("Catalog")
    .audit_mask_fields([])
    .table_name("catalog_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("name", DataType.Text).column_name("name").log_policy("plain").required()).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("entry_list", "Entry").local("id").foreign("catalog").many())
)

_Entry_DESCRIPTOR = (EntityDescriptor("Entry")
    .audit_mask_fields(["name"])
    .table_name("entry_data").property(PropertyDescriptor("id", DataType.I64).column_name("id").log_policy("plain").is_id().required()).property(PropertyDescriptor("catalog", DataType.I64).column_name("catalog").log_policy("plain").required()).property(PropertyDescriptor("name", DataType.Text).column_name("name").log_policy("plain").required()).property(PropertyDescriptor("born_at", DataType.Timestamp).column_name("born_at").log_policy("plain").required().fixed_by_runtime(insert=True).on_create_from_context("now")).property(PropertyDescriptor("touched_at", DataType.Timestamp).column_name("touched_at").log_policy("plain").required().fixed_by_runtime(insert=True, update=True).on_create_from_context("now").on_update_from_context("now")).property(PropertyDescriptor("version", DataType.I64).column_name("version").log_policy("plain").is_version().required()).relation(RelationDescriptor("catalog", "Catalog").local("catalog").foreign("id"))
)

async def _ensure_generated_bootstrap_once(context):
    previous_actor = context.user_identifier() if hasattr(context, 'user_identifier') else None
    previous_category = context.get_resource('bootstrapCategory')
    if hasattr(context, 'set_user_identifier'):
        context.set_user_identifier('teaql-generated-bootstrap')
    context.insert_resource('bootstrapCategory', 'runtime-bootstrap')
    try:
        catalog_1 = await (Q.catalogs().with_id_is(1).comment('what: locate generated bootstrap entity').purpose('why: idempotent runtime bootstrap').execute_for_one(context))
        if catalog_1 is None:
            catalog_1 = Catalog._teaql_new_with_fixed_id(1)
            catalog_1.update_name("Catalog")
            try:
                await catalog_1.audit_as('create model root Catalog(1)').save(context)
            except Exception as _teaql_create_error:
                for _teaql_attempt in range(5):
                    catalog_1 = await (Q.catalogs().with_id_is(1).comment('what: recover concurrent bootstrap').purpose('why: make generated bootstrap idempotent').execute_for_one(context))
                    if catalog_1 is not None:
                        break
                    if _teaql_attempt < 4:
                        await asyncio.sleep((_teaql_attempt + 1) * 0.01)
                if catalog_1 is None:
                    raise _teaql_create_error
        context.with_active_root(ContextEntityRef("Catalog", 1))
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
_CHECKER_PRESENTATION = CheckerPresentationModel.from_json("{\"schema\":\"teaql.checker-model/v1\",\"revision\":\"sha256:6499e0ef58931c3d57f98303285ad7d8cc498b658a8be72890e0431a6e158a25\",\"entities\":{\"Catalog\":{\"labels\":{\"en\":\"catalog\",\"zh-CN\":\"目录\"},\"fields\":[{\"name\":\"entry_list\",\"targetType\":\"Entry\",\"labels\":{\"en\":\"entry\",\"zh-CN\":\"明细\"},\"aliases\":[\"EntryList\",\"entryList\"]},{\"name\":\"id\",\"labels\":{\"en\":\"id\"},\"aliases\":[\"Id\"]},{\"name\":\"name\",\"labels\":{\"en\":\"name\",\"zh-CN\":\"名称\"},\"aliases\":[\"Name\"]},{\"name\":\"version\",\"labels\":{\"en\":\"version\"},\"aliases\":[\"Version\"]}]},\"Entry\":{\"labels\":{\"en\":\"entry\",\"zh-CN\":\"明细\"},\"fields\":[{\"name\":\"born_at\",\"labels\":{\"en\":\"born at\"},\"aliases\":[\"BornAt\",\"bornAt\"]},{\"name\":\"catalog\",\"targetType\":\"Catalog\",\"labels\":{\"en\":\"catalog\",\"zh-CN\":\"目录\"},\"aliases\":[\"Catalog\"]},{\"name\":\"id\",\"labels\":{\"en\":\"id\"},\"aliases\":[\"Id\"]},{\"name\":\"name\",\"labels\":{\"en\":\"name\",\"zh-CN\":\"名称\"},\"aliases\":[\"Name\"]},{\"name\":\"touched_at\",\"labels\":{\"en\":\"touched at\"},\"aliases\":[\"TouchedAt\",\"touchedAt\"]},{\"name\":\"version\",\"labels\":{\"en\":\"version\"},\"aliases\":[\"Version\"]}]}}}")
GENERATED_RUNTIME_MODULE = (RuntimeModule().entity(Catalog)
    .schema_entity(_Catalog_DESCRIPTOR)
    .checker("Catalog", _CatalogChecker())
    .wire_metadata("Catalog", create_wire_entity_metadata("Catalog", ["id", "name", "version"], JsonFieldNamingProfile.parse("camelCase"), {"id": ["id"], "name": ["name"], "version": ["version"]})).entity(Entry)
    .schema_entity(_Entry_DESCRIPTOR)
    .checker("Entry", _EntryChecker())
    .wire_metadata("Entry", create_wire_entity_metadata("Entry", ["id", "catalog", "name", "born_at", "touched_at", "version"], JsonFieldNamingProfile.parse("camelCase"), {"id": ["id"], "catalog": ["catalog"], "name": ["name"], "born_at": ["born_at"], "touched_at": ["touched_at"], "version": ["version"]}))
    .checker_presentation(_CHECKER_PRESENTATION)
    .generated_bootstrap(_ensure_generated_bootstrap)
)