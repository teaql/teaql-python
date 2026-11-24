from teaql.core.mutation import InsertCommand, UpdateCommand, DeleteCommand, MutationRequest
from teaql.core.mutation_version import validate_mutation_versions
from teaql.core.list import SmartList
from teaql.core.value import Value
from teaql.core.request_intent import MutationIntent
from teaql.core.projection_properties import ProjectionProperties
from teaql.runtime.loaded_scalar_snapshot import LoadedScalarSnapshots
from teaql.core.entity_creation import EntityCreationError, EntityCreationState
from teaql.runtime import CheckException, CheckResult, EntityKey, EntityRoot, ObjectLocation
from teaql.runtime import EntityJSONField, EntityJSONSchema, JsonFieldNamingProfile
from importlib import import_module
from copy import copy
from models.platform import Platform
from models.school_type import SchoolType


class _TeaqlFields:
    ID_PROPERTY_MEMBER = "id"
    ID_PROPERTY_COLUMN = "id"
    ID_PROPERTY_MODEL = "id"
    PLATFORM_PROPERTY_MEMBER = "platform"
    PLATFORM_PROPERTY_COLUMN = "platform"
    PLATFORM_PROPERTY_MODEL = "platform"
    SCHOOL_TYPE_PROPERTY_MEMBER = "schoolType"
    SCHOOL_TYPE_PROPERTY_COLUMN = "school_type"
    SCHOOL_TYPE_PROPERTY_MODEL = "school_type"
    NAME_PROPERTY_MEMBER = "name"
    NAME_PROPERTY_COLUMN = "name"
    NAME_PROPERTY_MODEL = "name"
    ADDRESS_PROPERTY_MEMBER = "address"
    ADDRESS_PROPERTY_COLUMN = "address"
    ADDRESS_PROPERTY_MODEL = "address"
    ESTABLISHED_DATE_PROPERTY_MEMBER = "establishedDate"
    ESTABLISHED_DATE_PROPERTY_COLUMN = "established_date"
    ESTABLISHED_DATE_PROPERTY_MODEL = "established_date"
    STUDENT_CAPACITY_PROPERTY_MEMBER = "studentCapacity"
    STUDENT_CAPACITY_PROPERTY_COLUMN = "student_capacity"
    STUDENT_CAPACITY_PROPERTY_MODEL = "student_capacity"
    ACTIVE_PROPERTY_MEMBER = "active"
    ACTIVE_PROPERTY_COLUMN = "active"
    ACTIVE_PROPERTY_MODEL = "active"
    CREATE_TIME_PROPERTY_MEMBER = "createTime"
    CREATE_TIME_PROPERTY_COLUMN = "create_time"
    CREATE_TIME_PROPERTY_MODEL = "create_time"
    UPDATE_TIME_PROPERTY_MEMBER = "updateTime"
    UPDATE_TIME_PROPERTY_COLUMN = "update_time"
    UPDATE_TIME_PROPERTY_MODEL = "update_time"
    VERSION_PROPERTY_MEMBER = "version"
    VERSION_PROPERTY_COLUMN = "version"
    VERSION_PROPERTY_MODEL = "version"

class School:
    _teaql_json_schema = EntityJSONSchema("School", (
        EntityJSONField(_TeaqlFields.ID_PROPERTY_MODEL, _TeaqlFields.ID_PROPERTY_MEMBER, "id"),
        EntityJSONField(_TeaqlFields.PLATFORM_PROPERTY_MODEL, _TeaqlFields.PLATFORM_PROPERTY_MEMBER, "reference", factory=lambda: Platform),
        EntityJSONField(_TeaqlFields.SCHOOL_TYPE_PROPERTY_MODEL, _TeaqlFields.SCHOOL_TYPE_PROPERTY_MEMBER, "reference", factory=lambda: SchoolType),
        EntityJSONField(_TeaqlFields.NAME_PROPERTY_MODEL, _TeaqlFields.NAME_PROPERTY_MEMBER, "text"),
        EntityJSONField(_TeaqlFields.ADDRESS_PROPERTY_MODEL, _TeaqlFields.ADDRESS_PROPERTY_MEMBER, "text"),
        EntityJSONField(_TeaqlFields.ESTABLISHED_DATE_PROPERTY_MODEL, _TeaqlFields.ESTABLISHED_DATE_PROPERTY_MEMBER, "date"),
        EntityJSONField(_TeaqlFields.STUDENT_CAPACITY_PROPERTY_MODEL, _TeaqlFields.STUDENT_CAPACITY_PROPERTY_MEMBER, "integer"),
        EntityJSONField(_TeaqlFields.ACTIVE_PROPERTY_MODEL, _TeaqlFields.ACTIVE_PROPERTY_MEMBER, "boolean"),
        EntityJSONField(_TeaqlFields.CREATE_TIME_PROPERTY_MODEL, _TeaqlFields.CREATE_TIME_PROPERTY_MEMBER, "datetime"),
        EntityJSONField(_TeaqlFields.UPDATE_TIME_PROPERTY_MODEL, _TeaqlFields.UPDATE_TIME_PROPERTY_MEMBER, "datetime"),
        EntityJSONField(_TeaqlFields.VERSION_PROPERTY_MODEL, _TeaqlFields.VERSION_PROPERTY_MEMBER, "version"),
    ), profile=JsonFieldNamingProfile.parse("camelCase"))

    def to_json(self, *, profile=None):
        """Typed model JSON; no query, mutation or transport authorization."""
        return self._teaql_json_schema.dumps(self._teaql_json_view({}), profile=profile)

    def _teaql_json_view(self, seen):
        """Detached presentation state; never marks live relations as loaded."""
        if id(self) in seen:
            return seen[id(self)]
        view = copy(self)
        seen[id(self)] = view
        view._loaded_fields = set(self._loaded_fields)
        value = self.platform
        if hasattr(value, "_teaql_json_view"):
            view.platform = value._teaql_json_view(seen)
        value = self.schoolType
        if hasattr(value, "_teaql_json_view"):
            view.schoolType = value._teaql_json_view(seen)
        return view

    @classmethod
    def from_json(cls, payload, *, profile=None):
        """Hydrate only supplied fields into an independent mutation boundary."""
        return cls._teaql_json_schema.loads(cls, payload, profile=profile)

    @classmethod
    def refer(cls, entity_id):
        return cls._teaql_from_record(id=entity_id)

    @classmethod
    def _teaql_from_reserved_id(cls, entity_id):
        """Generated Q plumbing, called only after Context reservation."""
        EntityCreationState.RESERVED.require_reserved(entity_id)
        entity = object.__new__(cls)
        entity._teaql_initialize_record(EntityCreationState.RESERVED, id=entity_id)
        return entity

    @classmethod
    def _teaql_from_record(cls, **kwargs):
        """Hydration never allocates an ID or creates insert intent."""
        entity = object.__new__(cls)
        entity._teaql_initialize_record(EntityCreationState.HYDRATED, **kwargs)
        return entity

    def _teaql_force_create(self):
        self._creation_state.require_reserved(getattr(self, "id", None))
        self._action = "Create"
        self._entity_root.mark_as_new(self._teaql_entity_key())
        return self

    def __init__(self, **kwargs):
        raise EntityCreationError()

    def _teaql_initialize_record(self, creation_state, **kwargs):
        self._creation_state = creation_state
        self._entity_root = kwargs.pop("_entity_root", None) or EntityRoot()
        if _TeaqlFields.ID_PROPERTY_COLUMN in kwargs and _TeaqlFields.ID_PROPERTY_MEMBER not in kwargs:
            kwargs[_TeaqlFields.ID_PROPERTY_MEMBER] = kwargs.pop(_TeaqlFields.ID_PROPERTY_COLUMN)
        if _TeaqlFields.PLATFORM_PROPERTY_COLUMN in kwargs and _TeaqlFields.PLATFORM_PROPERTY_MEMBER not in kwargs:
            kwargs[_TeaqlFields.PLATFORM_PROPERTY_MEMBER] = kwargs.pop(_TeaqlFields.PLATFORM_PROPERTY_COLUMN)
        if _TeaqlFields.SCHOOL_TYPE_PROPERTY_COLUMN in kwargs and _TeaqlFields.SCHOOL_TYPE_PROPERTY_MEMBER not in kwargs:
            kwargs[_TeaqlFields.SCHOOL_TYPE_PROPERTY_MEMBER] = kwargs.pop(_TeaqlFields.SCHOOL_TYPE_PROPERTY_COLUMN)
        if _TeaqlFields.NAME_PROPERTY_COLUMN in kwargs and _TeaqlFields.NAME_PROPERTY_MEMBER not in kwargs:
            kwargs[_TeaqlFields.NAME_PROPERTY_MEMBER] = kwargs.pop(_TeaqlFields.NAME_PROPERTY_COLUMN)
        if _TeaqlFields.ADDRESS_PROPERTY_COLUMN in kwargs and _TeaqlFields.ADDRESS_PROPERTY_MEMBER not in kwargs:
            kwargs[_TeaqlFields.ADDRESS_PROPERTY_MEMBER] = kwargs.pop(_TeaqlFields.ADDRESS_PROPERTY_COLUMN)
        if _TeaqlFields.ESTABLISHED_DATE_PROPERTY_COLUMN in kwargs and _TeaqlFields.ESTABLISHED_DATE_PROPERTY_MEMBER not in kwargs:
            kwargs[_TeaqlFields.ESTABLISHED_DATE_PROPERTY_MEMBER] = kwargs.pop(_TeaqlFields.ESTABLISHED_DATE_PROPERTY_COLUMN)
        if _TeaqlFields.STUDENT_CAPACITY_PROPERTY_COLUMN in kwargs and _TeaqlFields.STUDENT_CAPACITY_PROPERTY_MEMBER not in kwargs:
            kwargs[_TeaqlFields.STUDENT_CAPACITY_PROPERTY_MEMBER] = kwargs.pop(_TeaqlFields.STUDENT_CAPACITY_PROPERTY_COLUMN)
        if _TeaqlFields.ACTIVE_PROPERTY_COLUMN in kwargs and _TeaqlFields.ACTIVE_PROPERTY_MEMBER not in kwargs:
            kwargs[_TeaqlFields.ACTIVE_PROPERTY_MEMBER] = kwargs.pop(_TeaqlFields.ACTIVE_PROPERTY_COLUMN)
        if _TeaqlFields.CREATE_TIME_PROPERTY_COLUMN in kwargs and _TeaqlFields.CREATE_TIME_PROPERTY_MEMBER not in kwargs:
            kwargs[_TeaqlFields.CREATE_TIME_PROPERTY_MEMBER] = kwargs.pop(_TeaqlFields.CREATE_TIME_PROPERTY_COLUMN)
        if _TeaqlFields.UPDATE_TIME_PROPERTY_COLUMN in kwargs and _TeaqlFields.UPDATE_TIME_PROPERTY_MEMBER not in kwargs:
            kwargs[_TeaqlFields.UPDATE_TIME_PROPERTY_MEMBER] = kwargs.pop(_TeaqlFields.UPDATE_TIME_PROPERTY_COLUMN)
        if _TeaqlFields.VERSION_PROPERTY_COLUMN in kwargs and _TeaqlFields.VERSION_PROPERTY_MEMBER not in kwargs:
            kwargs[_TeaqlFields.VERSION_PROPERTY_MEMBER] = kwargs.pop(_TeaqlFields.VERSION_PROPERTY_COLUMN)
        self._projection_properties = ProjectionProperties(kwargs,
            [_TeaqlFields.ID_PROPERTY_MEMBER, _TeaqlFields.PLATFORM_PROPERTY_MEMBER, _TeaqlFields.SCHOOL_TYPE_PROPERTY_MEMBER, _TeaqlFields.NAME_PROPERTY_MEMBER, _TeaqlFields.ADDRESS_PROPERTY_MEMBER, _TeaqlFields.ESTABLISHED_DATE_PROPERTY_MEMBER, _TeaqlFields.STUDENT_CAPACITY_PROPERTY_MEMBER, _TeaqlFields.ACTIVE_PROPERTY_MEMBER, _TeaqlFields.CREATE_TIME_PROPERTY_MEMBER, _TeaqlFields.UPDATE_TIME_PROPERTY_MEMBER, _TeaqlFields.VERSION_PROPERTY_MEMBER])
        self._action = "Create" if creation_state is EntityCreationState.RESERVED else "Update"
        self._comment = None
        self._loaded_fields = set(kwargs.keys())
        self.id = kwargs.get(_TeaqlFields.ID_PROPERTY_MEMBER)

        self.platform = kwargs.get(_TeaqlFields.PLATFORM_PROPERTY_MEMBER)

        self.schoolType = kwargs.get(_TeaqlFields.SCHOOL_TYPE_PROPERTY_MEMBER)

        self.name = kwargs.get(_TeaqlFields.NAME_PROPERTY_MEMBER)

        self.address = kwargs.get(_TeaqlFields.ADDRESS_PROPERTY_MEMBER)

        self.establishedDate = kwargs.get(_TeaqlFields.ESTABLISHED_DATE_PROPERTY_MEMBER)

        self.studentCapacity = kwargs.get(_TeaqlFields.STUDENT_CAPACITY_PROPERTY_MEMBER)

        self.active = kwargs.get(_TeaqlFields.ACTIVE_PROPERTY_MEMBER)

        self.createTime = kwargs.get(_TeaqlFields.CREATE_TIME_PROPERTY_MEMBER)

        self.updateTime = kwargs.get(_TeaqlFields.UPDATE_TIME_PROPERTY_MEMBER)

        self.version = kwargs.get(_TeaqlFields.VERSION_PROPERTY_MEMBER)

        if isinstance(self.platform, dict):
            self.platform = Platform._teaql_from_record(**self.platform)
        if isinstance(self.schoolType, dict):
            self.schoolType = SchoolType._teaql_from_record(**self.schoolType)
        self._ledger_id = getattr(self, "id", None)
        key = self._teaql_entity_key()
        if self._action == "Create":
            self._entity_root.mark_as_new(key)
        elif getattr(self, "version", None) is not None:
            self._entity_root.set_original_version(key, int(self.version))
        LoadedScalarSnapshots.capture(self, self._teaql_snapshot_values(), origin=creation_state)

    def _teaql_snapshot_values(self):
        payload = {}
        if _TeaqlFields.ID_PROPERTY_MEMBER in self._loaded_fields:
            payload[_TeaqlFields.ID_PROPERTY_COLUMN] = Value.I64(self.id)

        if _TeaqlFields.PLATFORM_PROPERTY_MEMBER in self._loaded_fields:
            payload[_TeaqlFields.PLATFORM_PROPERTY_COLUMN] = Value.I64(getattr(self.platform, "id", self.platform))

        if _TeaqlFields.SCHOOL_TYPE_PROPERTY_MEMBER in self._loaded_fields:
            payload[_TeaqlFields.SCHOOL_TYPE_PROPERTY_COLUMN] = Value.I64(getattr(self.schoolType, "id", self.schoolType))

        if _TeaqlFields.NAME_PROPERTY_MEMBER in self._loaded_fields:
            payload[_TeaqlFields.NAME_PROPERTY_COLUMN] = Value.Text(self.name)

        if _TeaqlFields.ADDRESS_PROPERTY_MEMBER in self._loaded_fields:
            payload[_TeaqlFields.ADDRESS_PROPERTY_COLUMN] = Value.Text(self.address)

        if _TeaqlFields.ESTABLISHED_DATE_PROPERTY_MEMBER in self._loaded_fields:
            payload[_TeaqlFields.ESTABLISHED_DATE_PROPERTY_COLUMN] = Value.Date(self.establishedDate)

        if _TeaqlFields.STUDENT_CAPACITY_PROPERTY_MEMBER in self._loaded_fields:
            payload[_TeaqlFields.STUDENT_CAPACITY_PROPERTY_COLUMN] = Value.I64(self.studentCapacity)

        if _TeaqlFields.ACTIVE_PROPERTY_MEMBER in self._loaded_fields:
            payload[_TeaqlFields.ACTIVE_PROPERTY_COLUMN] = Value.Bool(self.active)

        if _TeaqlFields.CREATE_TIME_PROPERTY_MEMBER in self._loaded_fields:
            payload[_TeaqlFields.CREATE_TIME_PROPERTY_COLUMN] = Value.DateTime(self.createTime)

        if _TeaqlFields.UPDATE_TIME_PROPERTY_MEMBER in self._loaded_fields:
            payload[_TeaqlFields.UPDATE_TIME_PROPERTY_COLUMN] = Value.DateTime(self.updateTime)

        if _TeaqlFields.VERSION_PROPERTY_MEMBER in self._loaded_fields:
            payload[_TeaqlFields.VERSION_PROPERTY_COLUMN] = Value.I64(self.version)

        return payload

    def _teaql_entity_key(self):
        return EntityKey("School", self._ledger_id)

    def _teaql_restore_fixed_values(self, values):
        """Runtime-owned restoration supplies only known, equal scalar values."""
        if _TeaqlFields.NAME_PROPERTY_MODEL in values:
            value = values[_TeaqlFields.NAME_PROPERTY_MODEL]
            raw = value.val if isinstance(value, Value) else value
            self.name = raw

        if _TeaqlFields.ADDRESS_PROPERTY_MODEL in values:
            value = values[_TeaqlFields.ADDRESS_PROPERTY_MODEL]
            raw = value.val if isinstance(value, Value) else value
            self.address = raw

        if _TeaqlFields.ESTABLISHED_DATE_PROPERTY_MODEL in values:
            value = values[_TeaqlFields.ESTABLISHED_DATE_PROPERTY_MODEL]
            raw = value.val if isinstance(value, Value) else value
            self.establishedDate = raw

        if _TeaqlFields.STUDENT_CAPACITY_PROPERTY_MODEL in values:
            value = values[_TeaqlFields.STUDENT_CAPACITY_PROPERTY_MODEL]
            raw = value.val if isinstance(value, Value) else value
            self.studentCapacity = raw

        if _TeaqlFields.ACTIVE_PROPERTY_MODEL in values:
            value = values[_TeaqlFields.ACTIVE_PROPERTY_MODEL]
            raw = value.val if isinstance(value, Value) else value
            self.active = raw

        if _TeaqlFields.CREATE_TIME_PROPERTY_MODEL in values:
            value = values[_TeaqlFields.CREATE_TIME_PROPERTY_MODEL]
            raw = value.val if isinstance(value, Value) else value
            self.createTime = raw

        if _TeaqlFields.UPDATE_TIME_PROPERTY_MODEL in values:
            value = values[_TeaqlFields.UPDATE_TIME_PROPERTY_MODEL]
            raw = value.val if isinstance(value, Value) else value
            self.updateTime = raw


        pass

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
        # Validate intent and creation provenance before callbacks/provider access.
        MutationIntent(self._comment)
        context._validate_generated_graph_input("School",
            lambda: self._teaql_validate_input_graph(context, set()))
        return await context.execute_graph_save(
            lambda session: self._teaql_save_within_graph(session.context, session),
            prepare=lambda session: self._teaql_prepare_graph(session.context, session), comment=self._comment)

    def _teaql_validate_input_graph(self, context, visited, parent_field=None, validate_required=False):
        if id(self) in visited:
            return
        visited.add(id(self))
        self._creation_state.validate_mutation(self._action, getattr(self, "id", None),
            LoadedScalarSnapshots.persisted_version(self), self._entity_root.has_pending(self._teaql_entity_key()))
        LoadedScalarSnapshots.discard_restored_fields(self, context)
        if self._entity_root.has_pending(self._teaql_entity_key()):
            ledger = dict(self._entity_root.current_change_set().changes()).get(self._teaql_entity_key(), {})
            context._validate_mutation_fields("School", ledger)
            if self._action == "Update":
                if _TeaqlFields.ID_PROPERTY_MEMBER not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property(_TeaqlFields.ID_PROPERTY_MODEL), message="Mutation requires a fully loaded entity", entity_type="School")])
                if _TeaqlFields.PLATFORM_PROPERTY_MEMBER not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property(_TeaqlFields.PLATFORM_PROPERTY_MODEL), message="Mutation requires a fully loaded entity", entity_type="School")])
                if _TeaqlFields.SCHOOL_TYPE_PROPERTY_MEMBER not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property(_TeaqlFields.SCHOOL_TYPE_PROPERTY_MODEL), message="Mutation requires a fully loaded entity", entity_type="School")])
                if _TeaqlFields.NAME_PROPERTY_MEMBER not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property(_TeaqlFields.NAME_PROPERTY_MODEL), message="Mutation requires a fully loaded entity", entity_type="School")])
                if _TeaqlFields.ADDRESS_PROPERTY_MEMBER not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property(_TeaqlFields.ADDRESS_PROPERTY_MODEL), message="Mutation requires a fully loaded entity", entity_type="School")])
                if _TeaqlFields.ESTABLISHED_DATE_PROPERTY_MEMBER not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property(_TeaqlFields.ESTABLISHED_DATE_PROPERTY_MODEL), message="Mutation requires a fully loaded entity", entity_type="School")])
                if _TeaqlFields.STUDENT_CAPACITY_PROPERTY_MEMBER not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property(_TeaqlFields.STUDENT_CAPACITY_PROPERTY_MODEL), message="Mutation requires a fully loaded entity", entity_type="School")])
                if _TeaqlFields.ACTIVE_PROPERTY_MEMBER not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property(_TeaqlFields.ACTIVE_PROPERTY_MODEL), message="Mutation requires a fully loaded entity", entity_type="School")])
                if _TeaqlFields.CREATE_TIME_PROPERTY_MEMBER not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property(_TeaqlFields.CREATE_TIME_PROPERTY_MODEL), message="Mutation requires a fully loaded entity", entity_type="School")])
                if _TeaqlFields.UPDATE_TIME_PROPERTY_MEMBER not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property(_TeaqlFields.UPDATE_TIME_PROPERTY_MODEL), message="Mutation requires a fully loaded entity", entity_type="School")])
                if _TeaqlFields.VERSION_PROPERTY_MEMBER not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property(_TeaqlFields.VERSION_PROPERTY_MODEL), message="Mutation requires a fully loaded entity", entity_type="School")])
            # Required business values may be supplied by customer Fix. Root,
            # canonical-key, version and completeness admission still runs first.
            _action, command = self._teaql_build_command()
            validate_mutation_versions(command)
            if validate_required:
                context._validate_required_mutation_input(command, parent_field=parent_field)

    async def _teaql_ensure_business_ids(self, context):
        if self._action != "Create":
            return

    async def _teaql_reserve_graph_ids(self, context, visited):
        object_identity = id(self)
        if object_identity in visited:
            return
        visited.add(object_identity)
        if self._action == "Create":
            self._creation_state.require_reserved(getattr(self, "id", None))
        await self._teaql_ensure_business_ids(context)

    async def _teaql_prepare_graph(self, context, session):
        # Internal IDs are already reserved by Context-bound construction.
        # Complete input/Fix checks before admitting the final mutation plan.
        self._teaql_validate_input_graph(context, set())
        session._generated.admit_graph(self)
        self._teaql_prepare_input_graph(context, set(), session)
        # Fix may edit a sibling or its version; re-admit the whole graph.
        self._teaql_validate_input_graph(context, set(), validate_required=True)
        await self._teaql_reserve_graph_ids(context, set())
        self._teaql_preflight_graph(context, session)
        session._seal_generated_plan()

    def _teaql_prepare_input_graph(self, context, visited, session):
        if id(self) in visited:
            return
        visited.add(id(self))
        session._generated.observe(self)
        LoadedScalarSnapshots.discard_restored_fields(self, context)
        if self._entity_root.has_pending(self._teaql_entity_key()):
            ledger = dict(self._entity_root.current_change_set().changes()).get(self._teaql_entity_key(), {})
            context._validate_mutation_fields("School", ledger)
            # A fresh invocation starts from caller-owned Create attributes,
            # not retained output from a previously rejected Fix invocation.
            action, cmd = self._teaql_build_command(include_fixed=False)
            session._generated.fix(self, action, cmd,
                deferred_fields=())

    def _teaql_graph_relations(self):
        return {}

    def _teaql_scalar_payload(self):
        payload = {}
        if _TeaqlFields.ID_PROPERTY_MEMBER in self._loaded_fields:
            payload[_TeaqlFields.ID_PROPERTY_COLUMN] = Value.I64(self.id)

        if _TeaqlFields.PLATFORM_PROPERTY_MEMBER in self._loaded_fields:
            reference = self.platform
            reference_id = getattr(reference, "id", reference)
            payload[_TeaqlFields.PLATFORM_PROPERTY_COLUMN] = (Value.Object(reference)
                if reference is not None and hasattr(reference, "id") and reference_id is None
                else Value.I64(reference_id))

        if _TeaqlFields.SCHOOL_TYPE_PROPERTY_MEMBER in self._loaded_fields:
            reference = self.schoolType
            reference_id = getattr(reference, "id", reference)
            payload[_TeaqlFields.SCHOOL_TYPE_PROPERTY_COLUMN] = (Value.Object(reference)
                if reference is not None and hasattr(reference, "id") and reference_id is None
                else Value.I64(reference_id))

        if _TeaqlFields.NAME_PROPERTY_MEMBER in self._loaded_fields:
            payload[_TeaqlFields.NAME_PROPERTY_COLUMN] = Value.Text(self.name)

        if _TeaqlFields.ADDRESS_PROPERTY_MEMBER in self._loaded_fields:
            payload[_TeaqlFields.ADDRESS_PROPERTY_COLUMN] = Value.Text(self.address)

        if _TeaqlFields.ESTABLISHED_DATE_PROPERTY_MEMBER in self._loaded_fields:
            payload[_TeaqlFields.ESTABLISHED_DATE_PROPERTY_COLUMN] = Value.Date(self.establishedDate)

        if _TeaqlFields.STUDENT_CAPACITY_PROPERTY_MEMBER in self._loaded_fields:
            payload[_TeaqlFields.STUDENT_CAPACITY_PROPERTY_COLUMN] = Value.I64(self.studentCapacity)

        if _TeaqlFields.ACTIVE_PROPERTY_MEMBER in self._loaded_fields:
            payload[_TeaqlFields.ACTIVE_PROPERTY_COLUMN] = Value.Bool(self.active)

        if _TeaqlFields.CREATE_TIME_PROPERTY_MEMBER in self._loaded_fields:
            payload[_TeaqlFields.CREATE_TIME_PROPERTY_COLUMN] = Value.DateTime(self.createTime)

        if _TeaqlFields.UPDATE_TIME_PROPERTY_MEMBER in self._loaded_fields:
            payload[_TeaqlFields.UPDATE_TIME_PROPERTY_COLUMN] = Value.DateTime(self.updateTime)

        if _TeaqlFields.VERSION_PROPERTY_MEMBER in self._loaded_fields:
            payload[_TeaqlFields.VERSION_PROPERTY_COLUMN] = Value.I64(self.version)

        return payload

    def _teaql_build_command(self, include_fixed=True):
        payload = self._teaql_scalar_payload()
        action = self._action
        if action == "Create" and include_fixed:
            # Preparation Fix values live in the ledger until commit. Rebuilding
            # from entity attributes alone must not discard those checked values.
            ledger = dict(self._entity_root.current_change_set().changes()).get(self._teaql_entity_key(), {})
            payload.update({field: value for field, value in ledger.items() if field not in ("id", "version")})
        elif action == "Update":
            ledger = dict(self._entity_root.current_change_set().changes()).get(self._teaql_entity_key(), {})
            payload = {field: value for field, value in ledger.items() if field not in ("id", "version")}
        if _TeaqlFields.PLATFORM_PROPERTY_COLUMN in payload:
            reference = payload[_TeaqlFields.PLATFORM_PROPERTY_COLUMN].val
            if reference is not None and hasattr(reference, "id") and reference.id is not None:
                payload[_TeaqlFields.PLATFORM_PROPERTY_COLUMN] = Value.I64(reference.id)
        if _TeaqlFields.SCHOOL_TYPE_PROPERTY_COLUMN in payload:
            reference = payload[_TeaqlFields.SCHOOL_TYPE_PROPERTY_COLUMN].val
            if reference is not None and hasattr(reference, "id") and reference.id is not None:
                payload[_TeaqlFields.SCHOOL_TYPE_PROPERTY_COLUMN] = Value.I64(reference.id)
        if action == "Create":
            cmd = InsertCommand("School", payload)
        elif action == "Update":
            original_version = self._entity_root.original_version(self._teaql_entity_key())
            cmd = UpdateCommand("School", Value.from_any(getattr(self, "id", None)),
                original_version if original_version is not None else getattr(self, "version", None))
            for key, value in payload.items():
                if key not in ("id", "version"): cmd.value(key, value)
        else:
            original_version = self._entity_root.original_version(self._teaql_entity_key())
            cmd = DeleteCommand("School", Value.from_any(getattr(self, "id", None)),
                original_version if original_version is not None else getattr(self, "version", None))
        if action != "Create":
            cmd.old_values = LoadedScalarSnapshots.values(self)
        return action, cmd

    def _teaql_preflight_graph(self, context, session, parent=None):
        if not session._generated.visit("plan", self):
            return
        if parent is None:
            MutationIntent(self._comment)
        scope = session.scope(self._teaql_entity_key(), parent, self._comment)
        session.capture_loaded_values("School", LoadedScalarSnapshots.values(self))
        if self._entity_root.has_pending(self._teaql_entity_key()):
            if self._action == "Update":
                if _TeaqlFields.ID_PROPERTY_MEMBER not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property(_TeaqlFields.ID_PROPERTY_MODEL), message="Mutation requires a fully loaded entity", entity_type="School")])
                if _TeaqlFields.PLATFORM_PROPERTY_MEMBER not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property(_TeaqlFields.PLATFORM_PROPERTY_MODEL), message="Mutation requires a fully loaded entity", entity_type="School")])
                if _TeaqlFields.SCHOOL_TYPE_PROPERTY_MEMBER not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property(_TeaqlFields.SCHOOL_TYPE_PROPERTY_MODEL), message="Mutation requires a fully loaded entity", entity_type="School")])
                if _TeaqlFields.NAME_PROPERTY_MEMBER not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property(_TeaqlFields.NAME_PROPERTY_MODEL), message="Mutation requires a fully loaded entity", entity_type="School")])
                if _TeaqlFields.ADDRESS_PROPERTY_MEMBER not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property(_TeaqlFields.ADDRESS_PROPERTY_MODEL), message="Mutation requires a fully loaded entity", entity_type="School")])
                if _TeaqlFields.ESTABLISHED_DATE_PROPERTY_MEMBER not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property(_TeaqlFields.ESTABLISHED_DATE_PROPERTY_MODEL), message="Mutation requires a fully loaded entity", entity_type="School")])
                if _TeaqlFields.STUDENT_CAPACITY_PROPERTY_MEMBER not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property(_TeaqlFields.STUDENT_CAPACITY_PROPERTY_MODEL), message="Mutation requires a fully loaded entity", entity_type="School")])
                if _TeaqlFields.ACTIVE_PROPERTY_MEMBER not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property(_TeaqlFields.ACTIVE_PROPERTY_MODEL), message="Mutation requires a fully loaded entity", entity_type="School")])
                if _TeaqlFields.CREATE_TIME_PROPERTY_MEMBER not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property(_TeaqlFields.CREATE_TIME_PROPERTY_MODEL), message="Mutation requires a fully loaded entity", entity_type="School")])
                if _TeaqlFields.UPDATE_TIME_PROPERTY_MEMBER not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property(_TeaqlFields.UPDATE_TIME_PROPERTY_MODEL), message="Mutation requires a fully loaded entity", entity_type="School")])
                if _TeaqlFields.VERSION_PROPERTY_MEMBER not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property(_TeaqlFields.VERSION_PROPERTY_MODEL), message="Mutation requires a fully loaded entity", entity_type="School")])
            action, cmd = self._teaql_build_command()
            action, cmd = session._generated.finalize(self, action, cmd)
            session._remember_prepared_mutation(self, action, cmd)

    async def _teaql_save_within_graph(self, context, session, parent=None):
        if not session._generated.visit("write", self):
            return self
        session._generated.validate()
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
                "Mutation provider did not return authoritative persisted state for School"
            )
        rollback_payload = {field: getattr(self, field, None) for field in self._loaded_fields | {"id", "version"}}
        rollback_snapshot = LoadedScalarSnapshots.values(self)
        rollback_origin = LoadedScalarSnapshots.origin(self)
        rollback_creation_state = self._creation_state
        rollback_ledger_id = self._ledger_id
        rollback_action = self._action
        rollback_loaded_fields = set(self._loaded_fields)
        old_key = self._teaql_entity_key()
        if _TeaqlFields.ID_PROPERTY_COLUMN in persisted:
            self.id = persisted[_TeaqlFields.ID_PROPERTY_COLUMN]
            self._loaded_fields.add(_TeaqlFields.ID_PROPERTY_MEMBER)
        elif _TeaqlFields.ID_PROPERTY_MEMBER in persisted:
            self.id = persisted[_TeaqlFields.ID_PROPERTY_MEMBER]
            self._loaded_fields.add(_TeaqlFields.ID_PROPERTY_MEMBER)
        if _TeaqlFields.PLATFORM_PROPERTY_COLUMN in persisted:
            self.platform = persisted[_TeaqlFields.PLATFORM_PROPERTY_COLUMN]
            self._loaded_fields.add(_TeaqlFields.PLATFORM_PROPERTY_MEMBER)
        elif _TeaqlFields.PLATFORM_PROPERTY_MEMBER in persisted:
            self.platform = persisted[_TeaqlFields.PLATFORM_PROPERTY_MEMBER]
            self._loaded_fields.add(_TeaqlFields.PLATFORM_PROPERTY_MEMBER)
        if _TeaqlFields.SCHOOL_TYPE_PROPERTY_COLUMN in persisted:
            self.schoolType = persisted[_TeaqlFields.SCHOOL_TYPE_PROPERTY_COLUMN]
            self._loaded_fields.add(_TeaqlFields.SCHOOL_TYPE_PROPERTY_MEMBER)
        elif _TeaqlFields.SCHOOL_TYPE_PROPERTY_MEMBER in persisted:
            self.schoolType = persisted[_TeaqlFields.SCHOOL_TYPE_PROPERTY_MEMBER]
            self._loaded_fields.add(_TeaqlFields.SCHOOL_TYPE_PROPERTY_MEMBER)
        if _TeaqlFields.NAME_PROPERTY_COLUMN in persisted:
            self.name = persisted[_TeaqlFields.NAME_PROPERTY_COLUMN]
            self._loaded_fields.add(_TeaqlFields.NAME_PROPERTY_MEMBER)
        elif _TeaqlFields.NAME_PROPERTY_MEMBER in persisted:
            self.name = persisted[_TeaqlFields.NAME_PROPERTY_MEMBER]
            self._loaded_fields.add(_TeaqlFields.NAME_PROPERTY_MEMBER)
        if _TeaqlFields.ADDRESS_PROPERTY_COLUMN in persisted:
            self.address = persisted[_TeaqlFields.ADDRESS_PROPERTY_COLUMN]
            self._loaded_fields.add(_TeaqlFields.ADDRESS_PROPERTY_MEMBER)
        elif _TeaqlFields.ADDRESS_PROPERTY_MEMBER in persisted:
            self.address = persisted[_TeaqlFields.ADDRESS_PROPERTY_MEMBER]
            self._loaded_fields.add(_TeaqlFields.ADDRESS_PROPERTY_MEMBER)
        if _TeaqlFields.ESTABLISHED_DATE_PROPERTY_COLUMN in persisted:
            self.establishedDate = persisted[_TeaqlFields.ESTABLISHED_DATE_PROPERTY_COLUMN]
            self._loaded_fields.add(_TeaqlFields.ESTABLISHED_DATE_PROPERTY_MEMBER)
        elif _TeaqlFields.ESTABLISHED_DATE_PROPERTY_MEMBER in persisted:
            self.establishedDate = persisted[_TeaqlFields.ESTABLISHED_DATE_PROPERTY_MEMBER]
            self._loaded_fields.add(_TeaqlFields.ESTABLISHED_DATE_PROPERTY_MEMBER)
        if _TeaqlFields.STUDENT_CAPACITY_PROPERTY_COLUMN in persisted:
            self.studentCapacity = persisted[_TeaqlFields.STUDENT_CAPACITY_PROPERTY_COLUMN]
            self._loaded_fields.add(_TeaqlFields.STUDENT_CAPACITY_PROPERTY_MEMBER)
        elif _TeaqlFields.STUDENT_CAPACITY_PROPERTY_MEMBER in persisted:
            self.studentCapacity = persisted[_TeaqlFields.STUDENT_CAPACITY_PROPERTY_MEMBER]
            self._loaded_fields.add(_TeaqlFields.STUDENT_CAPACITY_PROPERTY_MEMBER)
        if _TeaqlFields.ACTIVE_PROPERTY_COLUMN in persisted:
            self.active = persisted[_TeaqlFields.ACTIVE_PROPERTY_COLUMN]
            self._loaded_fields.add(_TeaqlFields.ACTIVE_PROPERTY_MEMBER)
        elif _TeaqlFields.ACTIVE_PROPERTY_MEMBER in persisted:
            self.active = persisted[_TeaqlFields.ACTIVE_PROPERTY_MEMBER]
            self._loaded_fields.add(_TeaqlFields.ACTIVE_PROPERTY_MEMBER)
        if _TeaqlFields.CREATE_TIME_PROPERTY_COLUMN in persisted:
            self.createTime = persisted[_TeaqlFields.CREATE_TIME_PROPERTY_COLUMN]
            self._loaded_fields.add(_TeaqlFields.CREATE_TIME_PROPERTY_MEMBER)
        elif _TeaqlFields.CREATE_TIME_PROPERTY_MEMBER in persisted:
            self.createTime = persisted[_TeaqlFields.CREATE_TIME_PROPERTY_MEMBER]
            self._loaded_fields.add(_TeaqlFields.CREATE_TIME_PROPERTY_MEMBER)
        if _TeaqlFields.UPDATE_TIME_PROPERTY_COLUMN in persisted:
            self.updateTime = persisted[_TeaqlFields.UPDATE_TIME_PROPERTY_COLUMN]
            self._loaded_fields.add(_TeaqlFields.UPDATE_TIME_PROPERTY_MEMBER)
        elif _TeaqlFields.UPDATE_TIME_PROPERTY_MEMBER in persisted:
            self.updateTime = persisted[_TeaqlFields.UPDATE_TIME_PROPERTY_MEMBER]
            self._loaded_fields.add(_TeaqlFields.UPDATE_TIME_PROPERTY_MEMBER)
        if _TeaqlFields.VERSION_PROPERTY_COLUMN in persisted:
            self.version = persisted[_TeaqlFields.VERSION_PROPERTY_COLUMN]
            self._loaded_fields.add(_TeaqlFields.VERSION_PROPERTY_MEMBER)
        elif _TeaqlFields.VERSION_PROPERTY_MEMBER in persisted:
            self.version = persisted[_TeaqlFields.VERSION_PROPERTY_MEMBER]
            self._loaded_fields.add(_TeaqlFields.VERSION_PROPERTY_MEMBER)
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
            self._creation_state = rollback_creation_state
            LoadedScalarSnapshots.restore(self, rollback_snapshot, origin=rollback_origin)
            if old_key != new_key:
                self._entity_root.rekey(new_key, old_key)
        session.after_rollback(rollback_entity)
        if action != "Delete":
            self._action = "Update"
        session._generated.accepted(self)
        if action != "Delete":
            await self._teaql_cascade_children(context, session, scope)
        def commit_entity():
            session._generated.validate()
            self._creation_state = EntityCreationState.HYDRATED
            LoadedScalarSnapshots.capture(self, self._teaql_snapshot_values())
            self._entity_root.clear_entity(new_key)
            if getattr(self, "version", None) is not None:
                self._entity_root.accept_committed_version(new_key, int(self.version))
            session._generated.accepted(self)
        session.after_commit(commit_entity)
        return self

    async def _teaql_cascade_children(self, context, session, scope):
        cascade_relations = []
        for relation_name, children, updater, member in cascade_relations:
            for index, child in enumerate(children):
                child._teaql_attach_root(self._entity_root)
                current = getattr(child, member, None)
                if (getattr(current, "id", current) != self.id
                        and (child._action == "Create" or member in child._loaded_fields)):
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
        if _TeaqlFields.ID_PROPERTY_MEMBER in self._loaded_fields and LoadedScalarSnapshots.same_value(self.id, value):
            return self
        self.id = value
        self._loaded_fields.add(_TeaqlFields.ID_PROPERTY_MEMBER)
        self._entity_root.set(self._teaql_entity_key(), _TeaqlFields.ID_PROPERTY_COLUMN, Value.from_any(value))
        return self

    def update_name(self, value):
        if _TeaqlFields.NAME_PROPERTY_MEMBER in self._loaded_fields and LoadedScalarSnapshots.same_value(self.name, value):
            return self
        self.name = value
        self._loaded_fields.add(_TeaqlFields.NAME_PROPERTY_MEMBER)
        self._entity_root.set(self._teaql_entity_key(), _TeaqlFields.NAME_PROPERTY_COLUMN, Value.from_any(value))
        return self

    def update_address(self, value):
        if _TeaqlFields.ADDRESS_PROPERTY_MEMBER in self._loaded_fields and LoadedScalarSnapshots.same_value(self.address, value):
            return self
        self.address = value
        self._loaded_fields.add(_TeaqlFields.ADDRESS_PROPERTY_MEMBER)
        self._entity_root.set(self._teaql_entity_key(), _TeaqlFields.ADDRESS_PROPERTY_COLUMN, Value.from_any(value))
        return self

    def update_established_date(self, value):
        if _TeaqlFields.ESTABLISHED_DATE_PROPERTY_MEMBER in self._loaded_fields and LoadedScalarSnapshots.same_value(self.establishedDate, value):
            return self
        self.establishedDate = value
        self._loaded_fields.add(_TeaqlFields.ESTABLISHED_DATE_PROPERTY_MEMBER)
        self._entity_root.set(self._teaql_entity_key(), _TeaqlFields.ESTABLISHED_DATE_PROPERTY_COLUMN, Value.from_any(value))
        return self

    def update_student_capacity(self, value):
        if _TeaqlFields.STUDENT_CAPACITY_PROPERTY_MEMBER in self._loaded_fields and LoadedScalarSnapshots.same_value(self.studentCapacity, value):
            return self
        self.studentCapacity = value
        self._loaded_fields.add(_TeaqlFields.STUDENT_CAPACITY_PROPERTY_MEMBER)
        self._entity_root.set(self._teaql_entity_key(), _TeaqlFields.STUDENT_CAPACITY_PROPERTY_COLUMN, Value.from_any(value))
        return self

    def update_active(self, value):
        if _TeaqlFields.ACTIVE_PROPERTY_MEMBER in self._loaded_fields and LoadedScalarSnapshots.same_value(self.active, value):
            return self
        self.active = value
        self._loaded_fields.add(_TeaqlFields.ACTIVE_PROPERTY_MEMBER)
        self._entity_root.set(self._teaql_entity_key(), _TeaqlFields.ACTIVE_PROPERTY_COLUMN, Value.from_any(value))
        return self

    def update_create_time(self, value):
        if _TeaqlFields.CREATE_TIME_PROPERTY_MEMBER in self._loaded_fields and LoadedScalarSnapshots.same_value(self.createTime, value):
            return self
        self.createTime = value
        self._loaded_fields.add(_TeaqlFields.CREATE_TIME_PROPERTY_MEMBER)
        self._entity_root.set(self._teaql_entity_key(), _TeaqlFields.CREATE_TIME_PROPERTY_COLUMN, Value.from_any(value))
        return self

    def update_update_time(self, value):
        if _TeaqlFields.UPDATE_TIME_PROPERTY_MEMBER in self._loaded_fields and LoadedScalarSnapshots.same_value(self.updateTime, value):
            return self
        self.updateTime = value
        self._loaded_fields.add(_TeaqlFields.UPDATE_TIME_PROPERTY_MEMBER)
        self._entity_root.set(self._teaql_entity_key(), _TeaqlFields.UPDATE_TIME_PROPERTY_COLUMN, Value.from_any(value))
        return self

    def update_version(self, value):
        if _TeaqlFields.VERSION_PROPERTY_MEMBER in self._loaded_fields and LoadedScalarSnapshots.same_value(self.version, value):
            return self
        self.version = value
        self._loaded_fields.add(_TeaqlFields.VERSION_PROPERTY_MEMBER)
        self._entity_root.set(self._teaql_entity_key(), _TeaqlFields.VERSION_PROPERTY_COLUMN, Value.from_any(value))
        return self
    def update_platform(self, value):
        assigned_id = getattr(value, "id", value) if value else None
        current = self.platform
        current_id = getattr(current, "id", current)
        if _TeaqlFields.PLATFORM_PROPERTY_MEMBER in self._loaded_fields and LoadedScalarSnapshots.same_value(current_id, assigned_id) and (assigned_id is not None or current is value):
            return self
        self.platform = value if value is not None and hasattr(value, "id") and assigned_id is None else assigned_id
        self._loaded_fields.add(_TeaqlFields.PLATFORM_PROPERTY_MEMBER)
        self._entity_root.set(self._teaql_entity_key(), _TeaqlFields.PLATFORM_PROPERTY_COLUMN,
            Value.Object(self.platform) if self.platform is not None and hasattr(self.platform, "id")
            else Value.from_any(self.platform))
        return self


    def update_school_type(self, value):
        assigned_id = getattr(value, "id", value) if value else None
        current = self.schoolType
        current_id = getattr(current, "id", current)
        if _TeaqlFields.SCHOOL_TYPE_PROPERTY_MEMBER in self._loaded_fields and LoadedScalarSnapshots.same_value(current_id, assigned_id) and (assigned_id is not None or current is value):
            return self
        self.schoolType = value if value is not None and hasattr(value, "id") and assigned_id is None else assigned_id
        self._loaded_fields.add(_TeaqlFields.SCHOOL_TYPE_PROPERTY_MEMBER)
        self._entity_root.set(self._teaql_entity_key(), _TeaqlFields.SCHOOL_TYPE_PROPERTY_COLUMN,
            Value.Object(self.schoolType) if self.schoolType is not None and hasattr(self.schoolType, "id")
            else Value.from_any(self.schoolType))
        return self
    def update_school_type_to_primary(self):
        self.schoolType = 1001
        self._loaded_fields.add(_TeaqlFields.SCHOOL_TYPE_PROPERTY_MEMBER)
        self._entity_root.set(self._teaql_entity_key(), _TeaqlFields.SCHOOL_TYPE_PROPERTY_COLUMN, Value.from_any(self.schoolType))
        return self
    def update_school_type_to_secondary(self):
        self.schoolType = 1002
        self._loaded_fields.add(_TeaqlFields.SCHOOL_TYPE_PROPERTY_MEMBER)
        self._entity_root.set(self._teaql_entity_key(), _TeaqlFields.SCHOOL_TYPE_PROPERTY_COLUMN, Value.from_any(self.schoolType))
        return self
