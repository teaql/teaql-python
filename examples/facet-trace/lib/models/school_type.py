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
from models.platform import Platform


class SchoolType:
    _teaql_json_schema = EntityJSONSchema("SchoolType", (
        EntityJSONField("platform", "platform", "reference", factory=lambda: Platform),
        EntityJSONField("id", "id", "id"),
        EntityJSONField("name", "name", "text"),
        EntityJSONField("code", "code", "text"),
        EntityJSONField("display_order", "displayOrder", "decimal"),
        EntityJSONField("version", "version", "version"),
        EntityJSONField("school_list", "_school_list", "many", factory=lambda: getattr(import_module("models.school"), "School"), loaded_name="school_list")
    ), profile=JsonFieldNamingProfile.parse("camelCase"))

    def to_json(self, *, profile=None):
        """Typed model JSON; no query, mutation or transport authorization."""
        return self._teaql_json_schema.dumps(self, profile=profile)

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
        if "platform" in kwargs and "platform" not in kwargs:
            kwargs["platform"] = kwargs.pop("platform")
        if "id" in kwargs and "id" not in kwargs:
            kwargs["id"] = kwargs.pop("id")
        if "name" in kwargs and "name" not in kwargs:
            kwargs["name"] = kwargs.pop("name")
        if "code" in kwargs and "code" not in kwargs:
            kwargs["code"] = kwargs.pop("code")
        if "display_order" in kwargs and "displayOrder" not in kwargs:
            kwargs["displayOrder"] = kwargs.pop("display_order")
        if "version" in kwargs and "version" not in kwargs:
            kwargs["version"] = kwargs.pop("version")
        self._projection_properties = ProjectionProperties(kwargs,
            ["platform", "id", "name", "code", "displayOrder", "version", "school_list"])
        self._action = "Create" if creation_state is EntityCreationState.RESERVED else "Update"
        self._comment = None
        self._loaded_fields = set(kwargs.keys())
        self.platform = kwargs.get("platform")

        self.id = kwargs.get("id")

        self.name = kwargs.get("name")

        self.code = kwargs.get("code")

        self.displayOrder = kwargs.get("displayOrder")

        self.version = kwargs.get("version")

        if isinstance(self.platform, dict):
            self.platform = Platform._teaql_from_record(**self.platform)
        self._school_list = kwargs.get("school_list", [])
        if "school_list" in kwargs or creation_state is EntityCreationState.RESERVED:
            self._loaded_fields.add("school_list")
        if self._school_list:
            from models.school import School
            source = self._school_list
            hydrated = [
                item if isinstance(item, School) else School._teaql_from_record(_entity_root=self._entity_root, **item)
                for item in source
            ]
            self._school_list = (SmartList(hydrated, facets=source.facets, total_count=source.total_count)
                if isinstance(source, SmartList) else hydrated)
        self._ledger_id = getattr(self, "id", None)
        key = self._teaql_entity_key()
        if self._action == "Create":
            self._entity_root.mark_as_new(key)
        elif getattr(self, "version", None) is not None:
            self._entity_root.set_original_version(key, int(self.version))
        LoadedScalarSnapshots.capture(self, self._teaql_snapshot_values(), origin=creation_state)

    def _teaql_snapshot_values(self):
        payload = {}
        if "platform" in self._loaded_fields:
            payload["platform"] = Value.I64(getattr(self.platform, "id", self.platform))

        if "id" in self._loaded_fields:
            payload["id"] = Value.I64(self.id)

        if "name" in self._loaded_fields:
            payload["name"] = Value.Text(self.name)

        if "code" in self._loaded_fields:
            payload["code"] = Value.Text(self.code)

        if "displayOrder" in self._loaded_fields:
            payload["display_order"] = Value.Decimal(self.displayOrder)

        if "version" in self._loaded_fields:
            payload["version"] = Value.I64(self.version)

        return payload

    def _teaql_entity_key(self):
        return EntityKey("SchoolType", self._ledger_id)

    def get_dynamic_property(self, name):
        return self._projection_properties.get(name)

    def _teaql_attach_root(self, root):
        if self._entity_root is not root:
            root.merge_entity_from(self._entity_root, self._teaql_entity_key())
            self._entity_root = root
        for child in self._school_list:
            child._teaql_attach_root(root)
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
        self._teaql_validate_input_graph(context, set())
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
            context._validate_mutation_fields("SchoolType", ledger)
            if self._action == "Update":
                if "platform" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("platform"), message="Mutation requires a fully loaded entity", entity_type="SchoolType")])
                if "id" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("id"), message="Mutation requires a fully loaded entity", entity_type="SchoolType")])
                if "name" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("name"), message="Mutation requires a fully loaded entity", entity_type="SchoolType")])
                if "code" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("code"), message="Mutation requires a fully loaded entity", entity_type="SchoolType")])
                if "displayOrder" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("display_order"), message="Mutation requires a fully loaded entity", entity_type="SchoolType")])
                if "version" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("version"), message="Mutation requires a fully loaded entity", entity_type="SchoolType")])
            # Required business values may be supplied by customer Fix. Root,
            # canonical-key, version and completeness admission still runs first.
            _action, command = self._teaql_build_command()
            validate_mutation_versions(command)
            if validate_required:
                context._validate_required_mutation_input(command, parent_field=parent_field)
        for index, child in enumerate(self._school_list):
            try:
                child._teaql_validate_input_graph(context, visited, "school_type", validate_required=validate_required)
            except CheckException as error:
                prefix = ObjectLocation().property("school_list").index(index)
                raise CheckException([
                    v.prefixed_by(prefix)
                    for v in error.violations
                ]) from error

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
        for child in self._school_list:
            child._teaql_attach_root(self._entity_root)
            await child._teaql_reserve_graph_ids(context, visited)

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
        LoadedScalarSnapshots.discard_restored_fields(self, context)
        session._generated.observe(self)
        if self._entity_root.has_pending(self._teaql_entity_key()):
            ledger = dict(self._entity_root.current_change_set().changes()).get(self._teaql_entity_key(), {})
            context._validate_mutation_fields("SchoolType", ledger)
            # A fresh invocation starts from caller-owned Create attributes,
            # not retained output from a previously rejected Fix invocation.
            action, cmd = self._teaql_build_command(include_fixed=False)
            session._generated.fix(self, action, cmd,
                deferred_fields=())
        for index, child in enumerate(self._school_list):
            child._teaql_attach_root(self._entity_root)
            # A missing read projection is unknown, not a request to reparent a child.
            # Only new entities or a loaded FK can establish a changed association.
            current = getattr(child, "schoolType", None)
            if (current is not self and getattr(current, "id", current) != self.id
                    and (child._action == "Create" or "schoolType" in child._loaded_fields)):
                child.update_school_type(self)
            try:
                child._teaql_prepare_input_graph(context, visited, session)
            except CheckException as error:
                prefix = ObjectLocation().property("school_list").index(index)
                raise CheckException([
                    v.prefixed_by(prefix)
                    for v in error.violations
                ]) from error

    def _teaql_graph_relations(self):
        return {"school_list": tuple(self._school_list),}

    def _teaql_scalar_payload(self):
        payload = {}
        if "platform" in self._loaded_fields:
            reference = self.platform
            reference_id = getattr(reference, "id", reference)
            payload["platform"] = (Value.Object(reference)
                if reference is not None and hasattr(reference, "id") and reference_id is None
                else Value.I64(reference_id))

        if "id" in self._loaded_fields:
            payload["id"] = Value.I64(self.id)

        if "name" in self._loaded_fields:
            payload["name"] = Value.Text(self.name)

        if "code" in self._loaded_fields:
            payload["code"] = Value.Text(self.code)

        if "displayOrder" in self._loaded_fields:
            payload["display_order"] = Value.Decimal(self.displayOrder)

        if "version" in self._loaded_fields:
            payload["version"] = Value.I64(self.version)

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
        if "platform" in payload:
            reference = payload["platform"].val
            if reference is not None and hasattr(reference, "id") and reference.id is not None:
                payload["platform"] = Value.I64(reference.id)
        if action == "Create":
            cmd = InsertCommand("SchoolType", payload)
        elif action == "Update":
            original_version = self._entity_root.original_version(self._teaql_entity_key())
            cmd = UpdateCommand("SchoolType", Value.from_any(getattr(self, "id", None)),
                original_version if original_version is not None else getattr(self, "version", None))
            for key, value in payload.items():
                if key not in ("id", "version"): cmd.value(key, value)
        else:
            original_version = self._entity_root.original_version(self._teaql_entity_key())
            cmd = DeleteCommand("SchoolType", Value.from_any(getattr(self, "id", None)),
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
        session.capture_loaded_values("SchoolType", LoadedScalarSnapshots.values(self))
        if self._entity_root.has_pending(self._teaql_entity_key()):
            if self._action == "Update":
                if "platform" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("platform"), message="Mutation requires a fully loaded entity", entity_type="SchoolType")])
                if "id" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("id"), message="Mutation requires a fully loaded entity", entity_type="SchoolType")])
                if "name" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("name"), message="Mutation requires a fully loaded entity", entity_type="SchoolType")])
                if "code" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("code"), message="Mutation requires a fully loaded entity", entity_type="SchoolType")])
                if "displayOrder" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("display_order"), message="Mutation requires a fully loaded entity", entity_type="SchoolType")])
                if "version" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("version"), message="Mutation requires a fully loaded entity", entity_type="SchoolType")])
            action, cmd = self._teaql_build_command()
            try:
                action, cmd = session._generated.finalize(self, action, cmd)
            finally:
                for field, value in getattr(cmd, "values", {}).items():
                    if field not in ("id", "version"):
                        self._entity_root.set(self._teaql_entity_key(), field, value)
            session._remember_prepared_mutation(self, action, cmd)
        for index, child in enumerate(self._school_list):
            child._teaql_attach_root(self._entity_root)
            current = getattr(child, "schoolType", None)
            if (getattr(current, "id", current) != self.id
                    and (child._action == "Create" or "schoolType" in child._loaded_fields)):
                child.update_school_type(self)
            try:
                child._teaql_preflight_graph(context, session, scope)
            except CheckException as error:
                prefix = ObjectLocation().property("school_list").index(index)
                raise CheckException([
                    v.prefixed_by(prefix)
                    for v in error.violations
                ]) from error

    async def _teaql_save_within_graph(self, context, session, parent=None):
        if not session._generated.visit("write", self):
            return self
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
                "Mutation provider did not return authoritative persisted state for SchoolType"
            )
        rollback_payload = {field: getattr(self, field, None) for field in self._loaded_fields | {"id", "version"}}
        rollback_snapshot = LoadedScalarSnapshots.values(self)
        rollback_origin = LoadedScalarSnapshots.origin(self)
        rollback_creation_state = self._creation_state
        rollback_ledger_id = self._ledger_id
        rollback_action = self._action
        rollback_loaded_fields = set(self._loaded_fields)
        old_key = self._teaql_entity_key()
        if "platform" in persisted:
            self.platform = persisted["platform"]
            self._loaded_fields.add("platform")
        elif "platform" in persisted:
            self.platform = persisted["platform"]
            self._loaded_fields.add("platform")
        if "id" in persisted:
            self.id = persisted["id"]
            self._loaded_fields.add("id")
        elif "id" in persisted:
            self.id = persisted["id"]
            self._loaded_fields.add("id")
        if "name" in persisted:
            self.name = persisted["name"]
            self._loaded_fields.add("name")
        elif "name" in persisted:
            self.name = persisted["name"]
            self._loaded_fields.add("name")
        if "code" in persisted:
            self.code = persisted["code"]
            self._loaded_fields.add("code")
        elif "code" in persisted:
            self.code = persisted["code"]
            self._loaded_fields.add("code")
        if "display_order" in persisted:
            self.displayOrder = persisted["display_order"]
            self._loaded_fields.add("displayOrder")
        elif "displayOrder" in persisted:
            self.displayOrder = persisted["displayOrder"]
            self._loaded_fields.add("displayOrder")
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
            self._creation_state = EntityCreationState.HYDRATED
            LoadedScalarSnapshots.capture(self, self._teaql_snapshot_values())
            self._entity_root.clear_entity(new_key)
            if getattr(self, "version", None) is not None:
                self._entity_root.accept_committed_version(new_key, int(self.version))
        session.after_commit(commit_entity)
        return self

    async def _teaql_cascade_children(self, context, session, scope):
        cascade_relations = []
        cascade_relations.append(("school_list", self._school_list, "update_school_type", "schoolType"))
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
        if "id" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.id, value):
            return self
        self.id = value
        self._loaded_fields.add("id")
        self._entity_root.set(self._teaql_entity_key(), "id", Value.from_any(value))
        return self

    def update_name(self, value):
        if "name" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.name, value):
            return self
        self.name = value
        self._loaded_fields.add("name")
        self._entity_root.set(self._teaql_entity_key(), "name", Value.from_any(value))
        return self

    def update_code(self, value):
        if "code" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.code, value):
            return self
        self.code = value
        self._loaded_fields.add("code")
        self._entity_root.set(self._teaql_entity_key(), "code", Value.from_any(value))
        return self

    def update_display_order(self, value):
        if "displayOrder" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.displayOrder, value):
            return self
        self.displayOrder = value
        self._loaded_fields.add("displayOrder")
        self._entity_root.set(self._teaql_entity_key(), "display_order", Value.from_any(value))
        return self

    def update_version(self, value):
        if "version" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.version, value):
            return self
        self.version = value
        self._loaded_fields.add("version")
        self._entity_root.set(self._teaql_entity_key(), "version", Value.from_any(value))
        return self
    def update_platform(self, value):
        assigned_id = getattr(value, "id", value) if value else None
        current = self.platform
        current_id = getattr(current, "id", current)
        if "platform" in self._loaded_fields and LoadedScalarSnapshots.same_value(current_id, assigned_id) and (assigned_id is not None or current is value):
            return self
        self.platform = value if value is not None and hasattr(value, "id") and assigned_id is None else assigned_id
        self._loaded_fields.add("platform")
        self._entity_root.set(self._teaql_entity_key(), "platform",
            Value.Object(self.platform) if self.platform is not None and hasattr(self.platform, "id")
            else Value.from_any(self.platform))
        return self

    def school_list(self) -> list:
        self._loaded_fields.add("school_list")
        return self._school_list
