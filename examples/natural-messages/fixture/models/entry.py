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
from copy import copy
from models.catalog import Catalog


class Entry:
    _teaql_json_schema = EntityJSONSchema("Entry", (
        EntityJSONField("id", "id", "id"),
        EntityJSONField("catalog", "catalog", "reference", factory=lambda: Catalog),
        EntityJSONField("name", "name", "text"),
        EntityJSONField("born_at", "bornAt", "datetime"),
        EntityJSONField("touched_at", "touchedAt", "datetime"),
        EntityJSONField("version", "version", "version"),
    ), profile=JsonFieldNamingProfile.parse("camelCase"))
    _teaql_temporary_ids = itertools.count(1)

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
        value = self.catalog
        if hasattr(value, "_teaql_json_view"):
            view.catalog = value._teaql_json_view(seen)
        return view

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
        if "catalog" in kwargs and "catalog" not in kwargs:
            kwargs["catalog"] = kwargs.pop("catalog")
        if "name" in kwargs and "name" not in kwargs:
            kwargs["name"] = kwargs.pop("name")
        if "born_at" in kwargs and "bornAt" not in kwargs:
            kwargs["bornAt"] = kwargs.pop("born_at")
        if "touched_at" in kwargs and "touchedAt" not in kwargs:
            kwargs["touchedAt"] = kwargs.pop("touched_at")
        if "version" in kwargs and "version" not in kwargs:
            kwargs["version"] = kwargs.pop("version")
        self._projection_properties = ProjectionProperties(kwargs,
            ["id", "catalog", "name", "bornAt", "touchedAt", "version"])
        self._action = "Update" if kwargs.get("id") else "Create"
        self._comment = None
        self._loaded_fields = set(kwargs.keys())
        self.id = kwargs.get("id")

        self.catalog = kwargs.get("catalog")

        self.name = kwargs.get("name")

        self.bornAt = kwargs.get("bornAt")

        self.touchedAt = kwargs.get("touchedAt")

        self.version = kwargs.get("version")

        if isinstance(self.catalog, dict):
            self.catalog = Catalog(**self.catalog)
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

        if "catalog" in self._loaded_fields:
            payload["catalog"] = Value.I64(getattr(self.catalog, "id", self.catalog))

        if "name" in self._loaded_fields:
            payload["name"] = Value.Text(self.name)

        if "bornAt" in self._loaded_fields:
            payload["born_at"] = Value.DateTime(self.bornAt)

        if "touchedAt" in self._loaded_fields:
            payload["touched_at"] = Value.DateTime(self.touchedAt)

        if "version" in self._loaded_fields:
            payload["version"] = Value.I64(self.version)

        return payload

    def _teaql_entity_key(self):
        return EntityKey("Entry", self._ledger_id)

    def _teaql_restore_fixed_values(self, values):
        """Runtime-owned restoration supplies only known, equal scalar values."""
        if "name" in values:
            value = values["name"]
            raw = value.val if isinstance(value, Value) else value
            self.name = raw

        if "born_at" in values:
            value = values["born_at"]
            raw = value.val if isinstance(value, Value) else value
            self.bornAt = raw

        if "touched_at" in values:
            value = values["touched_at"]
            raw = value.val if isinstance(value, Value) else value
            self.touchedAt = raw


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
        # Validate the root reason before ID allocation or provider access.
        MutationIntent(self._comment)
        context._validate_generated_graph_input("Entry",
            lambda: self._teaql_validate_input_graph(context, set()))
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
            context._validate_mutation_fields("Entry", ledger)
            if self._action == "Update":
                if "id" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("id"), message="Mutation requires a fully loaded entity", entity_type="Entry")])
                if "catalog" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("catalog"), message="Mutation requires a fully loaded entity", entity_type="Entry")])
                if "name" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("name"), message="Mutation requires a fully loaded entity", entity_type="Entry")])
                if "bornAt" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("born_at"), message="Mutation requires a fully loaded entity", entity_type="Entry")])
                if "touchedAt" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("touched_at"), message="Mutation requires a fully loaded entity", entity_type="Entry")])
                if "version" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("version"), message="Mutation requires a fully loaded entity", entity_type="Entry")])
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
            self.id = int(await allocator("Entry"))
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
        session._generated.admit_graph(self)
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
        session = context._graph_session
        session._generated.observe(self)
        LoadedScalarSnapshots.discard_restored_fields(self, context)
        if self._entity_root.has_pending(self._teaql_entity_key()):
            ledger = dict(self._entity_root.current_change_set().changes()).get(self._teaql_entity_key(), {})
            context._validate_mutation_fields("Entry", ledger)
            _action, cmd = self._teaql_build_command()
            session._generated.fix(self, _action, cmd, deferred_fields=())

    def _teaql_graph_relations(self):
        return {}

    def _teaql_scalar_payload(self):
        payload = {}
        if "id" in self._loaded_fields:
            payload["id"] = Value.I64(self.id)

        if "catalog" in self._loaded_fields:
            reference = self.catalog
            reference_id = getattr(reference, "id", reference)
            payload["catalog"] = (Value.Object(reference)
                if reference is not None and hasattr(reference, "id") and reference_id is None
                else Value.I64(reference_id))

        if "name" in self._loaded_fields:
            payload["name"] = Value.Text(self.name)

        if "bornAt" in self._loaded_fields:
            payload["born_at"] = Value.DateTime(self.bornAt)

        if "touchedAt" in self._loaded_fields:
            payload["touched_at"] = Value.DateTime(self.touchedAt)

        if "version" in self._loaded_fields:
            payload["version"] = Value.I64(self.version)

        return payload

    def _teaql_build_command(self):
        payload = self._teaql_scalar_payload()
        action = self._action
        if action == "Update":
            ledger = dict(self._entity_root.current_change_set().changes()).get(self._teaql_entity_key(), {})
            payload = {field: value for field, value in ledger.items() if field not in ("id", "version")}
        if "catalog" in payload:
            reference = payload["catalog"].val
            if reference is not None and hasattr(reference, "id") and reference.id is not None:
                payload["catalog"] = Value.I64(reference.id)
        if action == "Create":
            cmd = InsertCommand("Entry", payload)
        elif action == "Update":
            original_version = self._entity_root.original_version(self._teaql_entity_key())
            cmd = UpdateCommand("Entry", Value.from_any(getattr(self, "id", None)),
                original_version if original_version is not None else getattr(self, "version", None))
            for key, value in payload.items():
                if key not in ("id", "version"): cmd.value(key, value)
        else:
            original_version = self._entity_root.original_version(self._teaql_entity_key())
            cmd = DeleteCommand("Entry", Value.from_any(getattr(self, "id", None)),
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
        session.capture_loaded_values("Entry", LoadedScalarSnapshots.values(self))
        if self._entity_root.has_pending(self._teaql_entity_key()):
            if self._action == "Update":
                if "id" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("id"), message="Mutation requires a fully loaded entity", entity_type="Entry")])
                if "catalog" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("catalog"), message="Mutation requires a fully loaded entity", entity_type="Entry")])
                if "name" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("name"), message="Mutation requires a fully loaded entity", entity_type="Entry")])
                if "bornAt" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("born_at"), message="Mutation requires a fully loaded entity", entity_type="Entry")])
                if "touchedAt" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("touched_at"), message="Mutation requires a fully loaded entity", entity_type="Entry")])
                if "version" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("version"), message="Mutation requires a fully loaded entity", entity_type="Entry")])
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
                "Mutation provider did not return authoritative persisted state for Entry"
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
        if "catalog" in persisted:
            self.catalog = persisted["catalog"]
            self._loaded_fields.add("catalog")
        elif "catalog" in persisted:
            self.catalog = persisted["catalog"]
            self._loaded_fields.add("catalog")
        if "name" in persisted:
            self.name = persisted["name"]
            self._loaded_fields.add("name")
        elif "name" in persisted:
            self.name = persisted["name"]
            self._loaded_fields.add("name")
        if "born_at" in persisted:
            self.bornAt = persisted["born_at"]
            self._loaded_fields.add("bornAt")
        elif "bornAt" in persisted:
            self.bornAt = persisted["bornAt"]
            self._loaded_fields.add("bornAt")
        if "touched_at" in persisted:
            self.touchedAt = persisted["touched_at"]
            self._loaded_fields.add("touchedAt")
        elif "touchedAt" in persisted:
            self.touchedAt = persisted["touchedAt"]
            self._loaded_fields.add("touchedAt")
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
        session._generated.accepted(self)

        if action != "Delete":
            await self._teaql_cascade_children(context, session, scope)
        def commit_entity():
            session._generated.validate()
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

    def update_name(self, value):
        if "name" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.name, value):
            return self
        self.name = value
        self._loaded_fields.add("name")
        self._entity_root.set(self._teaql_entity_key(), "name", Value.from_any(value))
        return self

    def update_born_at(self, value):
        if "bornAt" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.bornAt, value):
            return self
        self.bornAt = value
        self._loaded_fields.add("bornAt")
        self._entity_root.set(self._teaql_entity_key(), "born_at", Value.from_any(value))
        return self

    def update_touched_at(self, value):
        if "touchedAt" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.touchedAt, value):
            return self
        self.touchedAt = value
        self._loaded_fields.add("touchedAt")
        self._entity_root.set(self._teaql_entity_key(), "touched_at", Value.from_any(value))
        return self

    def update_version(self, value):
        if "version" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.version, value):
            return self
        self.version = value
        self._loaded_fields.add("version")
        self._entity_root.set(self._teaql_entity_key(), "version", Value.from_any(value))
        return self
    def update_catalog(self, value):
        assigned_id = getattr(value, "id", value) if value else None
        current = self.catalog
        current_id = getattr(current, "id", current)
        if "catalog" in self._loaded_fields and LoadedScalarSnapshots.same_value(current_id, assigned_id) and (assigned_id is not None or current is value):
            return self
        self.catalog = value if value is not None and hasattr(value, "id") and assigned_id is None else assigned_id
        self._loaded_fields.add("catalog")
        self._entity_root.set(self._teaql_entity_key(), "catalog",
            Value.Object(self.catalog) if self.catalog is not None and hasattr(self.catalog, "id")
            else Value.from_any(self.catalog))
        return self
