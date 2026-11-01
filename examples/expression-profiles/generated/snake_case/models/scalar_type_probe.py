from teaql.core.mutation import InsertCommand, UpdateCommand, DeleteCommand, MutationRequest
from teaql.core.list import SmartList
from teaql.core.value import Value
from teaql.core.request_intent import MutationIntent
from teaql.core.projection_properties import ProjectionProperties
from teaql.runtime.loaded_scalar_snapshot import LoadedScalarSnapshots
from teaql.runtime import CheckException, CheckResult, EntityKey, EntityRoot, ObjectLocation
from teaql.runtime import EntityJSONField, EntityJSONSchema, JsonFieldNamingProfile
from importlib import import_module
import itertools
from models.type_platform import TypePlatform


class ScalarTypeProbe:
    _teaql_json_schema = EntityJSONSchema("ScalarTypeProbe", (
        EntityJSONField("id", "id", "id"),
        EntityJSONField("type_platform", "typePlatform", "reference", factory=lambda: TypePlatform),
        EntityJSONField("required_string", "requiredString", "text"),
        EntityJSONField("optional_string", "optionalString", "text"),
        EntityJSONField("large_text", "largeText", "text"),
        EntityJSONField("required_boolean", "requiredBoolean", "boolean"),
        EntityJSONField("optional_boolean", "optionalBoolean", "boolean"),
        EntityJSONField("required_integer", "requiredInteger", "integer"),
        EntityJSONField("optional_integer", "optionalInteger", "integer"),
        EntityJSONField("required_long", "requiredLong", "long"),
        EntityJSONField("optional_long", "optionalLong", "long"),
        EntityJSONField("required_decimal", "requiredDecimal", "decimal"),
        EntityJSONField("optional_decimal", "optionalDecimal", "decimal"),
        EntityJSONField("required_float", "requiredFloat", "float"),
        EntityJSONField("optional_float", "optionalFloat", "float"),
        EntityJSONField("required_double", "requiredDouble", "double"),
        EntityJSONField("optional_double", "optionalDouble", "double"),
        EntityJSONField("required_date", "requiredDate", "date"),
        EntityJSONField("optional_date", "optionalDate", "date"),
        EntityJSONField("required_time", "requiredTime", "time"),
        EntityJSONField("optional_time", "optionalTime", "time"),
        EntityJSONField("required_datetime", "requiredDatetime", "datetime"),
        EntityJSONField("optional_datetime", "optionalDatetime", "datetime"),
        EntityJSONField("create_time", "createTime", "datetime"),
        EntityJSONField("update_time", "updateTime", "datetime"),
        EntityJSONField("version", "version", "version"),
    ), profile=JsonFieldNamingProfile.parse("snake_case"))
    _teaql_temporary_ids = itertools.count(1)

    def to_json(self, *, profile=None):
        """Typed model JSON; no query, mutation or transport authorization."""
        return self._teaql_json_schema.dumps(self, profile=profile)

    @classmethod
    def from_json(cls, payload, *, profile=None):
        """Hydrate only supplied fields into an independent mutation boundary."""
        return cls._teaql_json_schema.loads(cls, payload, profile=profile)

    @classmethod
    def refer(cls, entity_id):
        return cls(id=entity_id)

    @classmethod
    def _teaql_new_with_fixed_id(cls, entity_id):
        """Generated bootstrap capability; application code must not call it."""
        return cls(id=entity_id)._teaql_force_create()

    def _teaql_force_create(self):
        self._action = "Create"
        self._entity_root.mark_as_new(self._teaql_entity_key())
        return self

    def __init__(self, **kwargs):
        self._entity_root = kwargs.pop("_entity_root", None) or EntityRoot()
        if "id" in kwargs and "id" not in kwargs:
            kwargs["id"] = kwargs.pop("id")
        if "type_platform" in kwargs and "typePlatform" not in kwargs:
            kwargs["typePlatform"] = kwargs.pop("type_platform")
        if "required_string" in kwargs and "requiredString" not in kwargs:
            kwargs["requiredString"] = kwargs.pop("required_string")
        if "optional_string" in kwargs and "optionalString" not in kwargs:
            kwargs["optionalString"] = kwargs.pop("optional_string")
        if "large_text" in kwargs and "largeText" not in kwargs:
            kwargs["largeText"] = kwargs.pop("large_text")
        if "required_boolean" in kwargs and "requiredBoolean" not in kwargs:
            kwargs["requiredBoolean"] = kwargs.pop("required_boolean")
        if "optional_boolean" in kwargs and "optionalBoolean" not in kwargs:
            kwargs["optionalBoolean"] = kwargs.pop("optional_boolean")
        if "required_integer" in kwargs and "requiredInteger" not in kwargs:
            kwargs["requiredInteger"] = kwargs.pop("required_integer")
        if "optional_integer" in kwargs and "optionalInteger" not in kwargs:
            kwargs["optionalInteger"] = kwargs.pop("optional_integer")
        if "required_long" in kwargs and "requiredLong" not in kwargs:
            kwargs["requiredLong"] = kwargs.pop("required_long")
        if "optional_long" in kwargs and "optionalLong" not in kwargs:
            kwargs["optionalLong"] = kwargs.pop("optional_long")
        if "required_decimal" in kwargs and "requiredDecimal" not in kwargs:
            kwargs["requiredDecimal"] = kwargs.pop("required_decimal")
        if "optional_decimal" in kwargs and "optionalDecimal" not in kwargs:
            kwargs["optionalDecimal"] = kwargs.pop("optional_decimal")
        if "required_float" in kwargs and "requiredFloat" not in kwargs:
            kwargs["requiredFloat"] = kwargs.pop("required_float")
        if "optional_float" in kwargs and "optionalFloat" not in kwargs:
            kwargs["optionalFloat"] = kwargs.pop("optional_float")
        if "required_double" in kwargs and "requiredDouble" not in kwargs:
            kwargs["requiredDouble"] = kwargs.pop("required_double")
        if "optional_double" in kwargs and "optionalDouble" not in kwargs:
            kwargs["optionalDouble"] = kwargs.pop("optional_double")
        if "required_date" in kwargs and "requiredDate" not in kwargs:
            kwargs["requiredDate"] = kwargs.pop("required_date")
        if "optional_date" in kwargs and "optionalDate" not in kwargs:
            kwargs["optionalDate"] = kwargs.pop("optional_date")
        if "required_time" in kwargs and "requiredTime" not in kwargs:
            kwargs["requiredTime"] = kwargs.pop("required_time")
        if "optional_time" in kwargs and "optionalTime" not in kwargs:
            kwargs["optionalTime"] = kwargs.pop("optional_time")
        if "required_datetime" in kwargs and "requiredDatetime" not in kwargs:
            kwargs["requiredDatetime"] = kwargs.pop("required_datetime")
        if "optional_datetime" in kwargs and "optionalDatetime" not in kwargs:
            kwargs["optionalDatetime"] = kwargs.pop("optional_datetime")
        if "create_time" in kwargs and "createTime" not in kwargs:
            kwargs["createTime"] = kwargs.pop("create_time")
        if "update_time" in kwargs and "updateTime" not in kwargs:
            kwargs["updateTime"] = kwargs.pop("update_time")
        if "version" in kwargs and "version" not in kwargs:
            kwargs["version"] = kwargs.pop("version")
        self._projection_properties = ProjectionProperties(kwargs,
            ["id", "typePlatform", "requiredString", "optionalString", "largeText", "requiredBoolean", "optionalBoolean", "requiredInteger", "optionalInteger", "requiredLong", "optionalLong", "requiredDecimal", "optionalDecimal", "requiredFloat", "optionalFloat", "requiredDouble", "optionalDouble", "requiredDate", "optionalDate", "requiredTime", "optionalTime", "requiredDatetime", "optionalDatetime", "createTime", "updateTime", "version"])
        self._action = "Update" if kwargs.get("id") else "Create"
        self._comment = None
        self._loaded_fields = set(kwargs.keys())
        self.id = kwargs.get("id")

        self.typePlatform = kwargs.get("typePlatform")

        self.requiredString = kwargs.get("requiredString")

        self.optionalString = kwargs.get("optionalString")

        self.largeText = kwargs.get("largeText")

        self.requiredBoolean = kwargs.get("requiredBoolean")

        self.optionalBoolean = kwargs.get("optionalBoolean")

        self.requiredInteger = kwargs.get("requiredInteger")

        self.optionalInteger = kwargs.get("optionalInteger")

        self.requiredLong = kwargs.get("requiredLong")

        self.optionalLong = kwargs.get("optionalLong")

        self.requiredDecimal = kwargs.get("requiredDecimal")

        self.optionalDecimal = kwargs.get("optionalDecimal")

        self.requiredFloat = kwargs.get("requiredFloat")

        self.optionalFloat = kwargs.get("optionalFloat")

        self.requiredDouble = kwargs.get("requiredDouble")

        self.optionalDouble = kwargs.get("optionalDouble")

        self.requiredDate = kwargs.get("requiredDate")

        self.optionalDate = kwargs.get("optionalDate")

        self.requiredTime = kwargs.get("requiredTime")

        self.optionalTime = kwargs.get("optionalTime")

        self.requiredDatetime = kwargs.get("requiredDatetime")

        self.optionalDatetime = kwargs.get("optionalDatetime")

        self.createTime = kwargs.get("createTime")

        self.updateTime = kwargs.get("updateTime")

        self.version = kwargs.get("version")

        if isinstance(self.typePlatform, dict):
            self.typePlatform = TypePlatform(**self.typePlatform)
        self._ledger_id = getattr(self, "id", None)
        if self._ledger_id is None:
            self._ledger_id = -next(self._teaql_temporary_ids)
        key = self._teaql_entity_key()
        if self._action == "Create":
            self._entity_root.mark_as_new(key)
        elif getattr(self, "version", None) is not None:
            self._entity_root.set_original_version(key, int(self.version))
        LoadedScalarSnapshots.capture(self, self._teaql_snapshot_values())

    def _teaql_snapshot_values(self):
        payload = {}
        if "id" in self._loaded_fields:
            payload["id"] = Value.I64(self.id)

        if "typePlatform" in self._loaded_fields:
            payload["type_platform"] = Value.I64(getattr(self.typePlatform, "id", self.typePlatform))

        if "requiredString" in self._loaded_fields:
            payload["required_string"] = Value.Text(self.requiredString)

        if "optionalString" in self._loaded_fields:
            payload["optional_string"] = Value.Text(self.optionalString)

        if "largeText" in self._loaded_fields:
            payload["large_text"] = Value.Text(self.largeText)

        if "requiredBoolean" in self._loaded_fields:
            payload["required_boolean"] = Value.Bool(self.requiredBoolean)

        if "optionalBoolean" in self._loaded_fields:
            payload["optional_boolean"] = Value.Bool(self.optionalBoolean)

        if "requiredInteger" in self._loaded_fields:
            payload["required_integer"] = Value.I64(self.requiredInteger)

        if "optionalInteger" in self._loaded_fields:
            payload["optional_integer"] = Value.I64(self.optionalInteger)

        if "requiredLong" in self._loaded_fields:
            payload["required_long"] = Value.I64(self.requiredLong)

        if "optionalLong" in self._loaded_fields:
            payload["optional_long"] = Value.I64(self.optionalLong)

        if "requiredDecimal" in self._loaded_fields:
            payload["required_decimal"] = Value.Decimal(self.requiredDecimal)

        if "optionalDecimal" in self._loaded_fields:
            payload["optional_decimal"] = Value.Decimal(self.optionalDecimal)

        if "requiredFloat" in self._loaded_fields:
            payload["required_float"] = Value.F64(self.requiredFloat)

        if "optionalFloat" in self._loaded_fields:
            payload["optional_float"] = Value.F64(self.optionalFloat)

        if "requiredDouble" in self._loaded_fields:
            payload["required_double"] = Value.F64(self.requiredDouble)

        if "optionalDouble" in self._loaded_fields:
            payload["optional_double"] = Value.F64(self.optionalDouble)

        if "requiredDate" in self._loaded_fields:
            payload["required_date"] = Value.Date(self.requiredDate)

        if "optionalDate" in self._loaded_fields:
            payload["optional_date"] = Value.Date(self.optionalDate)

        if "requiredTime" in self._loaded_fields:
            payload["required_time"] = Value.Time(self.requiredTime)

        if "optionalTime" in self._loaded_fields:
            payload["optional_time"] = Value.Time(self.optionalTime)

        if "requiredDatetime" in self._loaded_fields:
            payload["required_datetime"] = Value.DateTime(self.requiredDatetime)

        if "optionalDatetime" in self._loaded_fields:
            payload["optional_datetime"] = Value.DateTime(self.optionalDatetime)

        if "createTime" in self._loaded_fields:
            payload["create_time"] = Value.DateTime(self.createTime)

        if "updateTime" in self._loaded_fields:
            payload["update_time"] = Value.DateTime(self.updateTime)

        if "version" in self._loaded_fields:
            payload["version"] = Value.I64(self.version)

        return payload

    def _teaql_entity_key(self):
        return EntityKey("ScalarTypeProbe", self._ledger_id)

    def get_dynamic_property(self, name):
        return self._projection_properties.get(name)

    def _teaql_attach_root(self, root):
        if self._entity_root is not root:
            root.merge_entity_from(self._entity_root, self._teaql_entity_key())
            self._entity_root = root
        return self
    def mark_for_deletion(self):
        self._action = "Delete"
        self._entity_root.mark_as_deleted(self._teaql_entity_key())
        return self

    def audit_as(self, comment: str):
        MutationIntent(comment)
        self._comment = comment
        return self

    async def save(self, context):
        # Validate the root reason before ID allocation or provider access.
        MutationIntent(self._comment)
        self._teaql_validate_input_graph(context, set())
        return await context.execute_graph_save(
            lambda session: self._teaql_save_within_graph(session.context, session),
            prepare=lambda session: self._teaql_prepare_graph(session.context, session), comment=self._comment)

    def _teaql_validate_input_graph(self, context, visited, parent_field=None):
        if id(self) in visited:
            return
        visited.add(id(self))
        LoadedScalarSnapshots.discard_restored_fields(self, context)
        if self._entity_root.has_pending(self._teaql_entity_key()):
            ledger = dict(self._entity_root.current_change_set().changes()).get(self._teaql_entity_key(), {})
            context._validate_mutation_fields("ScalarTypeProbe", ledger)
            if self._action == "Update":
                if "id" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("id"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "typePlatform" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("type_platform"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "requiredString" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("required_string"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "optionalString" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("optional_string"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "largeText" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("large_text"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "requiredBoolean" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("required_boolean"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "optionalBoolean" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("optional_boolean"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "requiredInteger" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("required_integer"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "optionalInteger" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("optional_integer"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "requiredLong" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("required_long"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "optionalLong" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("optional_long"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "requiredDecimal" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("required_decimal"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "optionalDecimal" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("optional_decimal"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "requiredFloat" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("required_float"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "optionalFloat" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("optional_float"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "requiredDouble" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("required_double"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "optionalDouble" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("optional_double"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "requiredDate" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("required_date"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "optionalDate" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("optional_date"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "requiredTime" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("required_time"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "optionalTime" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("optional_time"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "requiredDatetime" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("required_datetime"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "optionalDatetime" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("optional_datetime"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "createTime" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("create_time"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "updateTime" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("update_time"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "version" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("version"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
            _action, command = self._teaql_build_command()
            context._validate_required_mutation_input(command, parent_field=parent_field)

    async def _teaql_ensure_business_ids(self, context):
        if self._action != "Create":
            return

    async def _teaql_reserve_graph_ids(self, context, visited):
        object_identity = id(self)
        if object_identity in visited:
            return
        visited.add(object_identity)
        if self._action == "Create" and getattr(self, "id", None) is None:
            service = context.require_resource("dataService")
            allocator = getattr(service, "next_id", None)
            if not callable(allocator):
                raise RuntimeError(
                    "Configured dataService does not support stable ID reservation"
                )
            old_key = self._teaql_entity_key()
            self.id = int(await allocator("ScalarTypeProbe"))
            self._loaded_fields.add("id")
            self._ledger_id = self.id
            new_key = self._teaql_entity_key()
            self._entity_root.rekey(old_key, new_key)
            self._entity_root.set(new_key, "id", Value.I64(self.id))
        await self._teaql_ensure_business_ids(context)

    async def _teaql_prepare_graph(self, context, session):
        # Complete all input/Fix checks before reserving any graph identity.
        # Stable IDs then make the final policy plan and TraceScope concrete.
        self._teaql_validate_input_graph(context, set())
        self._teaql_prepare_input_graph(context, set())
        # Fix may edit a sibling or its version; re-admit the whole graph before IDs.
        self._teaql_validate_input_graph(context, set())
        await self._teaql_reserve_graph_ids(context, set())
        self._teaql_preflight_graph(context, session)
        session._seal_generated_plan()

    def _teaql_prepare_input_graph(self, context, visited):
        if id(self) in visited:
            return
        visited.add(id(self))
        LoadedScalarSnapshots.discard_restored_fields(self, context)
        if self._entity_root.has_pending(self._teaql_entity_key()):
            ledger = dict(self._entity_root.current_change_set().changes()).get(self._teaql_entity_key(), {})
            context._validate_mutation_fields("ScalarTypeProbe", ledger)
            _action, cmd = self._teaql_build_command()
            try:
                context._check_and_fix_mutation_input(cmd, deferred_fields=())
            finally:
                for field, value in getattr(cmd, "values", {}).items():
                    if field not in ("id", "version"):
                        self._entity_root.set(self._teaql_entity_key(), field, value)

    def _teaql_scalar_payload(self):
        payload = {}
        if "id" in self._loaded_fields:
            payload["id"] = Value.I64(self.id)

        if "typePlatform" in self._loaded_fields:
            reference = self.typePlatform
            reference_id = getattr(reference, "id", reference)
            payload["type_platform"] = (Value.Object(reference)
                if reference is not None and hasattr(reference, "id") and reference_id is None
                else Value.I64(reference_id))

        if "requiredString" in self._loaded_fields:
            payload["required_string"] = Value.Text(self.requiredString)

        if "optionalString" in self._loaded_fields:
            payload["optional_string"] = Value.Text(self.optionalString)

        if "largeText" in self._loaded_fields:
            payload["large_text"] = Value.Text(self.largeText)

        if "requiredBoolean" in self._loaded_fields:
            payload["required_boolean"] = Value.Bool(self.requiredBoolean)

        if "optionalBoolean" in self._loaded_fields:
            payload["optional_boolean"] = Value.Bool(self.optionalBoolean)

        if "requiredInteger" in self._loaded_fields:
            payload["required_integer"] = Value.I64(self.requiredInteger)

        if "optionalInteger" in self._loaded_fields:
            payload["optional_integer"] = Value.I64(self.optionalInteger)

        if "requiredLong" in self._loaded_fields:
            payload["required_long"] = Value.I64(self.requiredLong)

        if "optionalLong" in self._loaded_fields:
            payload["optional_long"] = Value.I64(self.optionalLong)

        if "requiredDecimal" in self._loaded_fields:
            payload["required_decimal"] = Value.Decimal(self.requiredDecimal)

        if "optionalDecimal" in self._loaded_fields:
            payload["optional_decimal"] = Value.Decimal(self.optionalDecimal)

        if "requiredFloat" in self._loaded_fields:
            payload["required_float"] = Value.F64(self.requiredFloat)

        if "optionalFloat" in self._loaded_fields:
            payload["optional_float"] = Value.F64(self.optionalFloat)

        if "requiredDouble" in self._loaded_fields:
            payload["required_double"] = Value.F64(self.requiredDouble)

        if "optionalDouble" in self._loaded_fields:
            payload["optional_double"] = Value.F64(self.optionalDouble)

        if "requiredDate" in self._loaded_fields:
            payload["required_date"] = Value.Date(self.requiredDate)

        if "optionalDate" in self._loaded_fields:
            payload["optional_date"] = Value.Date(self.optionalDate)

        if "requiredTime" in self._loaded_fields:
            payload["required_time"] = Value.Time(self.requiredTime)

        if "optionalTime" in self._loaded_fields:
            payload["optional_time"] = Value.Time(self.optionalTime)

        if "requiredDatetime" in self._loaded_fields:
            payload["required_datetime"] = Value.DateTime(self.requiredDatetime)

        if "optionalDatetime" in self._loaded_fields:
            payload["optional_datetime"] = Value.DateTime(self.optionalDatetime)

        if "createTime" in self._loaded_fields:
            payload["create_time"] = Value.DateTime(self.createTime)

        if "updateTime" in self._loaded_fields:
            payload["update_time"] = Value.DateTime(self.updateTime)

        if "version" in self._loaded_fields:
            payload["version"] = Value.I64(self.version)

        return payload

    def _teaql_build_command(self):
        payload = self._teaql_scalar_payload()
        action = self._action
        if action == "Update":
            ledger = dict(self._entity_root.current_change_set().changes()).get(self._teaql_entity_key(), {})
            payload = {field: value for field, value in ledger.items() if field not in ("id", "version")}
        if "type_platform" in payload:
            reference = payload["type_platform"].val
            if reference is not None and hasattr(reference, "id") and reference.id is not None:
                payload["type_platform"] = Value.I64(reference.id)
        if action == "Create":
            cmd = InsertCommand("ScalarTypeProbe", payload)
        elif action == "Update":
            original_version = self._entity_root.original_version(self._teaql_entity_key())
            cmd = UpdateCommand("ScalarTypeProbe", Value.from_any(getattr(self, "id", None)),
                original_version if original_version is not None else getattr(self, "version", None))
            for key, value in payload.items():
                if key not in ("id", "version"): cmd.value(key, value)
        else:
            original_version = self._entity_root.original_version(self._teaql_entity_key())
            cmd = DeleteCommand("ScalarTypeProbe", Value.from_any(getattr(self, "id", None)),
                original_version if original_version is not None else getattr(self, "version", None))
        if action != "Create":
            cmd.old_values = LoadedScalarSnapshots.values(self)
        return action, cmd

    def _teaql_preflight_graph(self, context, session, parent=None):
        if parent is None:
            MutationIntent(self._comment)
        scope = session.scope(self._teaql_entity_key(), parent, self._comment)
        session.capture_loaded_values("ScalarTypeProbe", LoadedScalarSnapshots.values(self))
        if self._entity_root.has_pending(self._teaql_entity_key()):
            if self._action == "Update":
                if "id" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("id"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "typePlatform" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("type_platform"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "requiredString" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("required_string"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "optionalString" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("optional_string"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "largeText" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("large_text"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "requiredBoolean" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("required_boolean"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "optionalBoolean" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("optional_boolean"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "requiredInteger" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("required_integer"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "optionalInteger" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("optional_integer"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "requiredLong" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("required_long"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "optionalLong" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("optional_long"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "requiredDecimal" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("required_decimal"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "optionalDecimal" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("optional_decimal"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "requiredFloat" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("required_float"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "optionalFloat" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("optional_float"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "requiredDouble" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("required_double"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "optionalDouble" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("optional_double"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "requiredDate" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("required_date"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "optionalDate" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("optional_date"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "requiredTime" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("required_time"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "optionalTime" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("optional_time"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "requiredDatetime" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("required_datetime"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "optionalDatetime" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("optional_datetime"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "createTime" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("create_time"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "updateTime" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("update_time"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
                if "version" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("version"), message="Mutation requires a fully loaded entity", entity_type="ScalarTypeProbe")])
            action, cmd = self._teaql_build_command()
            try:
                context.preflight_mutation(cmd)
            finally:
                for field, value in getattr(cmd, "values", {}).items():
                    if field not in ("id", "version"):
                        self._entity_root.set(self._teaql_entity_key(), field, value)
            session._remember_prepared_mutation(self, action, cmd)

    async def _teaql_save_within_graph(self, context, session, parent=None):
        if parent is None:
            MutationIntent(self._comment)

        self._teaql_attach_root(self._entity_root)
        scope = session.scope(self._teaql_entity_key(), parent, self._comment)
        if not self._entity_root.has_pending(self._teaql_entity_key()):
            await self._teaql_cascade_children(context, session, scope)
            return self
        action, cmd = session._prepared_mutation(self)


        req = session.request(cmd, scope, self._entity_root, self._teaql_entity_key())

        # Execute the exact final checked command; no third Fix pass in SQL.
        context.mark_mutation_checked(cmd)
        service = context.require_resource("dataService")
        result = await service.mutate(context, req)
        persisted = result.persisted_record
        if persisted is None:
            raise RuntimeError(
                "Mutation provider did not return authoritative persisted state for ScalarTypeProbe"
            )
        rollback_payload = {field: getattr(self, field, None) for field in self._loaded_fields | {"id", "version"}}
        rollback_snapshot = LoadedScalarSnapshots.values(self)
        rollback_ledger_id = self._ledger_id
        rollback_action = self._action
        rollback_loaded_fields = set(self._loaded_fields)
        old_key = self._teaql_entity_key()
        if "id" in persisted:
            self.id = persisted["id"]
            self._loaded_fields.add("id")
        elif "id" in persisted:
            self.id = persisted["id"]
            self._loaded_fields.add("id")
        if "type_platform" in persisted:
            self.typePlatform = persisted["type_platform"]
            self._loaded_fields.add("typePlatform")
        elif "typePlatform" in persisted:
            self.typePlatform = persisted["typePlatform"]
            self._loaded_fields.add("typePlatform")
        if "required_string" in persisted:
            self.requiredString = persisted["required_string"]
            self._loaded_fields.add("requiredString")
        elif "requiredString" in persisted:
            self.requiredString = persisted["requiredString"]
            self._loaded_fields.add("requiredString")
        if "optional_string" in persisted:
            self.optionalString = persisted["optional_string"]
            self._loaded_fields.add("optionalString")
        elif "optionalString" in persisted:
            self.optionalString = persisted["optionalString"]
            self._loaded_fields.add("optionalString")
        if "large_text" in persisted:
            self.largeText = persisted["large_text"]
            self._loaded_fields.add("largeText")
        elif "largeText" in persisted:
            self.largeText = persisted["largeText"]
            self._loaded_fields.add("largeText")
        if "required_boolean" in persisted:
            self.requiredBoolean = persisted["required_boolean"]
            self._loaded_fields.add("requiredBoolean")
        elif "requiredBoolean" in persisted:
            self.requiredBoolean = persisted["requiredBoolean"]
            self._loaded_fields.add("requiredBoolean")
        if "optional_boolean" in persisted:
            self.optionalBoolean = persisted["optional_boolean"]
            self._loaded_fields.add("optionalBoolean")
        elif "optionalBoolean" in persisted:
            self.optionalBoolean = persisted["optionalBoolean"]
            self._loaded_fields.add("optionalBoolean")
        if "required_integer" in persisted:
            self.requiredInteger = persisted["required_integer"]
            self._loaded_fields.add("requiredInteger")
        elif "requiredInteger" in persisted:
            self.requiredInteger = persisted["requiredInteger"]
            self._loaded_fields.add("requiredInteger")
        if "optional_integer" in persisted:
            self.optionalInteger = persisted["optional_integer"]
            self._loaded_fields.add("optionalInteger")
        elif "optionalInteger" in persisted:
            self.optionalInteger = persisted["optionalInteger"]
            self._loaded_fields.add("optionalInteger")
        if "required_long" in persisted:
            self.requiredLong = persisted["required_long"]
            self._loaded_fields.add("requiredLong")
        elif "requiredLong" in persisted:
            self.requiredLong = persisted["requiredLong"]
            self._loaded_fields.add("requiredLong")
        if "optional_long" in persisted:
            self.optionalLong = persisted["optional_long"]
            self._loaded_fields.add("optionalLong")
        elif "optionalLong" in persisted:
            self.optionalLong = persisted["optionalLong"]
            self._loaded_fields.add("optionalLong")
        if "required_decimal" in persisted:
            self.requiredDecimal = persisted["required_decimal"]
            self._loaded_fields.add("requiredDecimal")
        elif "requiredDecimal" in persisted:
            self.requiredDecimal = persisted["requiredDecimal"]
            self._loaded_fields.add("requiredDecimal")
        if "optional_decimal" in persisted:
            self.optionalDecimal = persisted["optional_decimal"]
            self._loaded_fields.add("optionalDecimal")
        elif "optionalDecimal" in persisted:
            self.optionalDecimal = persisted["optionalDecimal"]
            self._loaded_fields.add("optionalDecimal")
        if "required_float" in persisted:
            self.requiredFloat = persisted["required_float"]
            self._loaded_fields.add("requiredFloat")
        elif "requiredFloat" in persisted:
            self.requiredFloat = persisted["requiredFloat"]
            self._loaded_fields.add("requiredFloat")
        if "optional_float" in persisted:
            self.optionalFloat = persisted["optional_float"]
            self._loaded_fields.add("optionalFloat")
        elif "optionalFloat" in persisted:
            self.optionalFloat = persisted["optionalFloat"]
            self._loaded_fields.add("optionalFloat")
        if "required_double" in persisted:
            self.requiredDouble = persisted["required_double"]
            self._loaded_fields.add("requiredDouble")
        elif "requiredDouble" in persisted:
            self.requiredDouble = persisted["requiredDouble"]
            self._loaded_fields.add("requiredDouble")
        if "optional_double" in persisted:
            self.optionalDouble = persisted["optional_double"]
            self._loaded_fields.add("optionalDouble")
        elif "optionalDouble" in persisted:
            self.optionalDouble = persisted["optionalDouble"]
            self._loaded_fields.add("optionalDouble")
        if "required_date" in persisted:
            self.requiredDate = persisted["required_date"]
            self._loaded_fields.add("requiredDate")
        elif "requiredDate" in persisted:
            self.requiredDate = persisted["requiredDate"]
            self._loaded_fields.add("requiredDate")
        if "optional_date" in persisted:
            self.optionalDate = persisted["optional_date"]
            self._loaded_fields.add("optionalDate")
        elif "optionalDate" in persisted:
            self.optionalDate = persisted["optionalDate"]
            self._loaded_fields.add("optionalDate")
        if "required_time" in persisted:
            self.requiredTime = persisted["required_time"]
            self._loaded_fields.add("requiredTime")
        elif "requiredTime" in persisted:
            self.requiredTime = persisted["requiredTime"]
            self._loaded_fields.add("requiredTime")
        if "optional_time" in persisted:
            self.optionalTime = persisted["optional_time"]
            self._loaded_fields.add("optionalTime")
        elif "optionalTime" in persisted:
            self.optionalTime = persisted["optionalTime"]
            self._loaded_fields.add("optionalTime")
        if "required_datetime" in persisted:
            self.requiredDatetime = persisted["required_datetime"]
            self._loaded_fields.add("requiredDatetime")
        elif "requiredDatetime" in persisted:
            self.requiredDatetime = persisted["requiredDatetime"]
            self._loaded_fields.add("requiredDatetime")
        if "optional_datetime" in persisted:
            self.optionalDatetime = persisted["optional_datetime"]
            self._loaded_fields.add("optionalDatetime")
        elif "optionalDatetime" in persisted:
            self.optionalDatetime = persisted["optionalDatetime"]
            self._loaded_fields.add("optionalDatetime")
        if "create_time" in persisted:
            self.createTime = persisted["create_time"]
            self._loaded_fields.add("createTime")
        elif "createTime" in persisted:
            self.createTime = persisted["createTime"]
            self._loaded_fields.add("createTime")
        if "update_time" in persisted:
            self.updateTime = persisted["update_time"]
            self._loaded_fields.add("updateTime")
        elif "updateTime" in persisted:
            self.updateTime = persisted["updateTime"]
            self._loaded_fields.add("updateTime")
        if "version" in persisted:
            self.version = persisted["version"]
            self._loaded_fields.add("version")
        elif "version" in persisted:
            self.version = persisted["version"]
            self._loaded_fields.add("version")
        self._ledger_id = getattr(self, "id", self._ledger_id)
        new_key = self._teaql_entity_key()
        if old_key != new_key:
            self._entity_root.rekey(old_key, new_key)
        def rollback_entity():
            for field, value in rollback_payload.items():
                setattr(self, field, value)
            self._ledger_id = rollback_ledger_id
            self._action = rollback_action
            self._loaded_fields = rollback_loaded_fields
            LoadedScalarSnapshots.restore(self, rollback_snapshot)
            if old_key != new_key:
                self._entity_root.rekey(new_key, old_key)
        session.after_rollback(rollback_entity)
        if action != "Delete":
            self._action = "Update"

        if action != "Delete":
            await self._teaql_cascade_children(context, session, scope)
        def commit_entity():
            LoadedScalarSnapshots.capture(self, self._teaql_snapshot_values())
            self._entity_root.clear_entity(new_key)
            if getattr(self, "version", None) is not None:
                self._entity_root.accept_committed_version(new_key, int(self.version))
        session.after_commit(commit_entity)
        return self

    async def _teaql_cascade_children(self, context, session, scope):
        cascade_relations = []
        for relation_name, children, updater, member in cascade_relations:
            for index, child in enumerate(children):
                child._teaql_attach_root(self._entity_root)
                current = getattr(child, member, None)
                if getattr(current, "id", current) != self.id:
                    getattr(child, updater)(self)
                try:
                    await child._teaql_save_within_graph(context, session, scope)
                except CheckException as error:
                    prefix = ObjectLocation().property(relation_name).index(index)
                    raise CheckException([
                        violation.prefixed_by(prefix)
                        for violation in error.violations
                    ]) from error

    def update_id(self, value):
        if self._action != "Create":
            raise ValueError("ENTITY_ID_IMMUTABLE: an existing entity ID cannot be changed")
        value = int(value) if isinstance(value, str) and value.isdecimal() else value
        if type(value) is not int or not 0 < value <= 18446744073709551615:
            raise ValueError("ENTITY_ID_INVALID: an assigned unsigned-64 identity is required")
        old_key = self._teaql_entity_key()
        self._ledger_id = value
        self._entity_root.rekey(old_key, self._teaql_entity_key())
        if "id" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.id, value):
            return self
        self.id = value
        self._loaded_fields.add("id")
        self._entity_root.set(self._teaql_entity_key(), "id", Value.from_any(value))
        return self

    def update_required_string(self, value):
        if "requiredString" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.requiredString, value):
            return self
        self.requiredString = value
        self._loaded_fields.add("requiredString")
        self._entity_root.set(self._teaql_entity_key(), "required_string", Value.from_any(value))
        return self

    def update_optional_string(self, value):
        if "optionalString" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.optionalString, value):
            return self
        self.optionalString = value
        self._loaded_fields.add("optionalString")
        self._entity_root.set(self._teaql_entity_key(), "optional_string", Value.from_any(value))
        return self

    def update_large_text(self, value):
        if "largeText" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.largeText, value):
            return self
        self.largeText = value
        self._loaded_fields.add("largeText")
        self._entity_root.set(self._teaql_entity_key(), "large_text", Value.from_any(value))
        return self

    def update_required_boolean(self, value):
        if "requiredBoolean" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.requiredBoolean, value):
            return self
        self.requiredBoolean = value
        self._loaded_fields.add("requiredBoolean")
        self._entity_root.set(self._teaql_entity_key(), "required_boolean", Value.from_any(value))
        return self

    def update_optional_boolean(self, value):
        if "optionalBoolean" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.optionalBoolean, value):
            return self
        self.optionalBoolean = value
        self._loaded_fields.add("optionalBoolean")
        self._entity_root.set(self._teaql_entity_key(), "optional_boolean", Value.from_any(value))
        return self

    def update_required_integer(self, value):
        if "requiredInteger" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.requiredInteger, value):
            return self
        self.requiredInteger = value
        self._loaded_fields.add("requiredInteger")
        self._entity_root.set(self._teaql_entity_key(), "required_integer", Value.from_any(value))
        return self

    def update_optional_integer(self, value):
        if "optionalInteger" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.optionalInteger, value):
            return self
        self.optionalInteger = value
        self._loaded_fields.add("optionalInteger")
        self._entity_root.set(self._teaql_entity_key(), "optional_integer", Value.from_any(value))
        return self

    def update_required_long(self, value):
        if "requiredLong" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.requiredLong, value):
            return self
        self.requiredLong = value
        self._loaded_fields.add("requiredLong")
        self._entity_root.set(self._teaql_entity_key(), "required_long", Value.from_any(value))
        return self

    def update_optional_long(self, value):
        if "optionalLong" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.optionalLong, value):
            return self
        self.optionalLong = value
        self._loaded_fields.add("optionalLong")
        self._entity_root.set(self._teaql_entity_key(), "optional_long", Value.from_any(value))
        return self

    def update_required_decimal(self, value):
        if "requiredDecimal" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.requiredDecimal, value):
            return self
        self.requiredDecimal = value
        self._loaded_fields.add("requiredDecimal")
        self._entity_root.set(self._teaql_entity_key(), "required_decimal", Value.from_any(value))
        return self

    def update_optional_decimal(self, value):
        if "optionalDecimal" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.optionalDecimal, value):
            return self
        self.optionalDecimal = value
        self._loaded_fields.add("optionalDecimal")
        self._entity_root.set(self._teaql_entity_key(), "optional_decimal", Value.from_any(value))
        return self

    def update_required_float(self, value):
        if "requiredFloat" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.requiredFloat, value):
            return self
        self.requiredFloat = value
        self._loaded_fields.add("requiredFloat")
        self._entity_root.set(self._teaql_entity_key(), "required_float", Value.from_any(value))
        return self

    def update_optional_float(self, value):
        if "optionalFloat" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.optionalFloat, value):
            return self
        self.optionalFloat = value
        self._loaded_fields.add("optionalFloat")
        self._entity_root.set(self._teaql_entity_key(), "optional_float", Value.from_any(value))
        return self

    def update_required_double(self, value):
        if "requiredDouble" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.requiredDouble, value):
            return self
        self.requiredDouble = value
        self._loaded_fields.add("requiredDouble")
        self._entity_root.set(self._teaql_entity_key(), "required_double", Value.from_any(value))
        return self

    def update_optional_double(self, value):
        if "optionalDouble" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.optionalDouble, value):
            return self
        self.optionalDouble = value
        self._loaded_fields.add("optionalDouble")
        self._entity_root.set(self._teaql_entity_key(), "optional_double", Value.from_any(value))
        return self

    def update_required_date(self, value):
        if "requiredDate" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.requiredDate, value):
            return self
        self.requiredDate = value
        self._loaded_fields.add("requiredDate")
        self._entity_root.set(self._teaql_entity_key(), "required_date", Value.from_any(value))
        return self

    def update_optional_date(self, value):
        if "optionalDate" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.optionalDate, value):
            return self
        self.optionalDate = value
        self._loaded_fields.add("optionalDate")
        self._entity_root.set(self._teaql_entity_key(), "optional_date", Value.from_any(value))
        return self

    def update_required_time(self, value):
        if "requiredTime" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.requiredTime, value):
            return self
        self.requiredTime = value
        self._loaded_fields.add("requiredTime")
        self._entity_root.set(self._teaql_entity_key(), "required_time", Value.from_any(value))
        return self

    def update_optional_time(self, value):
        if "optionalTime" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.optionalTime, value):
            return self
        self.optionalTime = value
        self._loaded_fields.add("optionalTime")
        self._entity_root.set(self._teaql_entity_key(), "optional_time", Value.from_any(value))
        return self

    def update_required_datetime(self, value):
        if "requiredDatetime" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.requiredDatetime, value):
            return self
        self.requiredDatetime = value
        self._loaded_fields.add("requiredDatetime")
        self._entity_root.set(self._teaql_entity_key(), "required_datetime", Value.from_any(value))
        return self

    def update_optional_datetime(self, value):
        if "optionalDatetime" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.optionalDatetime, value):
            return self
        self.optionalDatetime = value
        self._loaded_fields.add("optionalDatetime")
        self._entity_root.set(self._teaql_entity_key(), "optional_datetime", Value.from_any(value))
        return self

    def update_create_time(self, value):
        if "createTime" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.createTime, value):
            return self
        self.createTime = value
        self._loaded_fields.add("createTime")
        self._entity_root.set(self._teaql_entity_key(), "create_time", Value.from_any(value))
        return self

    def update_update_time(self, value):
        if "updateTime" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.updateTime, value):
            return self
        self.updateTime = value
        self._loaded_fields.add("updateTime")
        self._entity_root.set(self._teaql_entity_key(), "update_time", Value.from_any(value))
        return self

    def update_version(self, value):
        if "version" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.version, value):
            return self
        self.version = value
        self._loaded_fields.add("version")
        self._entity_root.set(self._teaql_entity_key(), "version", Value.from_any(value))
        return self
    def update_type_platform(self, value):
        assigned_id = getattr(value, "id", value) if value else None
        current = self.typePlatform
        current_id = getattr(current, "id", current)
        if "typePlatform" in self._loaded_fields and LoadedScalarSnapshots.same_value(current_id, assigned_id) and (assigned_id is not None or current is value):
            return self
        self.typePlatform = value if value is not None and hasattr(value, "id") and assigned_id is None else assigned_id
        self._loaded_fields.add("typePlatform")
        self._entity_root.set(self._teaql_entity_key(), "type_platform",
            Value.Object(self.typePlatform) if self.typePlatform is not None and hasattr(self.typePlatform, "id")
            else Value.from_any(self.typePlatform))
        return self
