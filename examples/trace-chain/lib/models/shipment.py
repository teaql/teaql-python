from teaql.core.mutation import InsertCommand, UpdateCommand, DeleteCommand, MutationRequest
from teaql.core.mutation_version import validate_mutation_versions
from teaql.core.list import SmartList
from teaql.core.value import Value
from teaql.core.request_intent import MutationIntent
from teaql.core.projection_properties import ProjectionProperties
from teaql.runtime.loaded_scalar_snapshot import LoadedScalarSnapshots
from teaql.runtime import CheckException, CheckResult, EntityKey, EntityRoot, ObjectLocation
from teaql.runtime import EntityJSONField, EntityJSONSchema, JsonFieldNamingProfile
from importlib import import_module
import itertools
from models.customer_order import CustomerOrder


class Shipment:
    _teaql_json_schema = EntityJSONSchema("Shipment", (
        EntityJSONField("id", "id", "id"),
        EntityJSONField("customer_order", "customerOrder", "reference", factory=lambda: CustomerOrder),
        EntityJSONField("reference_code", "referenceCode", "text"),
        EntityJSONField("version", "version", "version"),
    ), profile=JsonFieldNamingProfile.parse("camelCase"))
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
        if "customer_order" in kwargs and "customerOrder" not in kwargs:
            kwargs["customerOrder"] = kwargs.pop("customer_order")
        if "reference_code" in kwargs and "referenceCode" not in kwargs:
            kwargs["referenceCode"] = kwargs.pop("reference_code")
        if "version" in kwargs and "version" not in kwargs:
            kwargs["version"] = kwargs.pop("version")
        self._projection_properties = ProjectionProperties(kwargs,
            ["id", "customerOrder", "referenceCode", "version"])
        self._action = "Update" if kwargs.get("id") else "Create"
        self._comment = None
        self._loaded_fields = set(kwargs.keys())
        self.id = kwargs.get("id")

        self.customerOrder = kwargs.get("customerOrder")

        self.referenceCode = kwargs.get("referenceCode")

        self.version = kwargs.get("version")

        if isinstance(self.customerOrder, dict):
            self.customerOrder = CustomerOrder(**self.customerOrder)
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

        if "customerOrder" in self._loaded_fields:
            payload["customer_order"] = Value.I64(getattr(self.customerOrder, "id", self.customerOrder))

        if "referenceCode" in self._loaded_fields:
            payload["reference_code"] = Value.Text(self.referenceCode)

        if "version" in self._loaded_fields:
            payload["version"] = Value.I64(self.version)

        return payload

    def _teaql_entity_key(self):
        return EntityKey("Shipment", self._ledger_id)

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

    def _teaql_validate_input_graph(self, context, visited, parent_field=None, validate_required=False):
        if id(self) in visited:
            return
        visited.add(id(self))
        LoadedScalarSnapshots.discard_restored_fields(self, context)
        if self._entity_root.has_pending(self._teaql_entity_key()):
            ledger = dict(self._entity_root.current_change_set().changes()).get(self._teaql_entity_key(), {})
            context._validate_mutation_fields("Shipment", ledger)
            if self._action == "Update":
                if "id" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("id"), message="Mutation requires a fully loaded entity", entity_type="Shipment")])
                if "customerOrder" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("customer_order"), message="Mutation requires a fully loaded entity", entity_type="Shipment")])
                if "referenceCode" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("reference_code"), message="Mutation requires a fully loaded entity", entity_type="Shipment")])
                if "version" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("version"), message="Mutation requires a fully loaded entity", entity_type="Shipment")])
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
        if self._action == "Create" and getattr(self, "id", None) is None:
            old_key = self._teaql_entity_key()
            self.id = await context.next_id("Shipment")
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
        self._teaql_prepare_input_graph(context, set(), session)
        # Fix may edit a sibling or its version; re-admit the whole graph before IDs.
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
            context._validate_mutation_fields("Shipment", ledger)
            # A fresh invocation starts from caller-owned Create attributes,
            # not retained output from a previously rejected Fix invocation.
            action, cmd = self._teaql_build_command(include_fixed=False)
            session._generated.fix(self, action, cmd,
                deferred_fields=())

    def _teaql_graph_relations(self):
        return {}

    def _teaql_scalar_payload(self):
        payload = {}
        if "id" in self._loaded_fields:
            payload["id"] = Value.I64(self.id)

        if "customerOrder" in self._loaded_fields:
            reference = self.customerOrder
            reference_id = getattr(reference, "id", reference)
            payload["customer_order"] = (Value.Object(reference)
                if reference is not None and hasattr(reference, "id") and reference_id is None
                else Value.I64(reference_id))

        if "referenceCode" in self._loaded_fields:
            payload["reference_code"] = Value.Text(self.referenceCode)

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
        if "customer_order" in payload:
            reference = payload["customer_order"].val
            if reference is not None and hasattr(reference, "id") and reference.id is not None:
                payload["customer_order"] = Value.I64(reference.id)
        if action == "Create":
            cmd = InsertCommand("Shipment", payload)
        elif action == "Update":
            original_version = self._entity_root.original_version(self._teaql_entity_key())
            cmd = UpdateCommand("Shipment", Value.from_any(getattr(self, "id", None)),
                original_version if original_version is not None else getattr(self, "version", None))
            for key, value in payload.items():
                if key not in ("id", "version"): cmd.value(key, value)
        else:
            original_version = self._entity_root.original_version(self._teaql_entity_key())
            cmd = DeleteCommand("Shipment", Value.from_any(getattr(self, "id", None)),
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
        session.capture_loaded_values("Shipment", LoadedScalarSnapshots.values(self))
        if self._entity_root.has_pending(self._teaql_entity_key()):
            if self._action == "Update":
                if "id" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("id"), message="Mutation requires a fully loaded entity", entity_type="Shipment")])
                if "customerOrder" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("customer_order"), message="Mutation requires a fully loaded entity", entity_type="Shipment")])
                if "referenceCode" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("reference_code"), message="Mutation requires a fully loaded entity", entity_type="Shipment")])
                if "version" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("version"), message="Mutation requires a fully loaded entity", entity_type="Shipment")])
            action, cmd = self._teaql_build_command()
            try:
                action, cmd = session._generated.finalize(self, action, cmd)
            finally:
                for field, value in getattr(cmd, "values", {}).items():
                    if field not in ("id", "version"):
                        self._entity_root.set(self._teaql_entity_key(), field, value)
            session._remember_prepared_mutation(self, action, cmd)

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
                "Mutation provider did not return authoritative persisted state for Shipment"
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
        if "customer_order" in persisted:
            self.customerOrder = persisted["customer_order"]
            self._loaded_fields.add("customerOrder")
        elif "customerOrder" in persisted:
            self.customerOrder = persisted["customerOrder"]
            self._loaded_fields.add("customerOrder")
        if "reference_code" in persisted:
            self.referenceCode = persisted["reference_code"]
            self._loaded_fields.add("referenceCode")
        elif "referenceCode" in persisted:
            self.referenceCode = persisted["referenceCode"]
            self._loaded_fields.add("referenceCode")
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

    def update_reference_code(self, value):
        if "referenceCode" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.referenceCode, value):
            return self
        self.referenceCode = value
        self._loaded_fields.add("referenceCode")
        self._entity_root.set(self._teaql_entity_key(), "reference_code", Value.from_any(value))
        return self

    def update_version(self, value):
        if "version" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.version, value):
            return self
        self.version = value
        self._loaded_fields.add("version")
        self._entity_root.set(self._teaql_entity_key(), "version", Value.from_any(value))
        return self
    def update_customer_order(self, value):
        assigned_id = getattr(value, "id", value) if value else None
        current = self.customerOrder
        current_id = getattr(current, "id", current)
        if "customerOrder" in self._loaded_fields and LoadedScalarSnapshots.same_value(current_id, assigned_id) and (assigned_id is not None or current is value):
            return self
        self.customerOrder = value if value is not None and hasattr(value, "id") and assigned_id is None else assigned_id
        self._loaded_fields.add("customerOrder")
        self._entity_root.set(self._teaql_entity_key(), "customer_order",
            Value.Object(self.customerOrder) if self.customerOrder is not None and hasattr(self.customerOrder, "id")
            else Value.from_any(self.customerOrder))
        return self
