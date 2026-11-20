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


class FreightQuote:
    _teaql_json_schema = EntityJSONSchema("FreightQuote", (
        EntityJSONField("id", "id", "id"),
        EntityJSONField("platform", "platform", "reference", factory=lambda: Platform),
        EntityJSONField("reference", "reference", "text"),
        EntityJSONField("amount", "amount", "decimal"),
        EntityJSONField("shipment_number", "shipmentNumber", "long"),
        EntityJSONField("package_count", "packageCount", "integer"),
        EntityJSONField("delivery_date", "deliveryDate", "date"),
        EntityJSONField("pickup_time", "pickupTime", "time"),
        EntityJSONField("quoted_at", "quotedAt", "datetime"),
        EntityJSONField("instructions", "instructions", "text"),
        EntityJSONField("version", "version", "version"),
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
        if "id" in kwargs and "id" not in kwargs:
            kwargs["id"] = kwargs.pop("id")
        if "platform" in kwargs and "platform" not in kwargs:
            kwargs["platform"] = kwargs.pop("platform")
        if "reference" in kwargs and "reference" not in kwargs:
            kwargs["reference"] = kwargs.pop("reference")
        if "amount" in kwargs and "amount" not in kwargs:
            kwargs["amount"] = kwargs.pop("amount")
        if "shipment_number" in kwargs and "shipmentNumber" not in kwargs:
            kwargs["shipmentNumber"] = kwargs.pop("shipment_number")
        if "package_count" in kwargs and "packageCount" not in kwargs:
            kwargs["packageCount"] = kwargs.pop("package_count")
        if "delivery_date" in kwargs and "deliveryDate" not in kwargs:
            kwargs["deliveryDate"] = kwargs.pop("delivery_date")
        if "pickup_time" in kwargs and "pickupTime" not in kwargs:
            kwargs["pickupTime"] = kwargs.pop("pickup_time")
        if "quoted_at" in kwargs and "quotedAt" not in kwargs:
            kwargs["quotedAt"] = kwargs.pop("quoted_at")
        if "instructions" in kwargs and "instructions" not in kwargs:
            kwargs["instructions"] = kwargs.pop("instructions")
        if "version" in kwargs and "version" not in kwargs:
            kwargs["version"] = kwargs.pop("version")
        self._projection_properties = ProjectionProperties(kwargs,
            ["id", "platform", "reference", "amount", "shipmentNumber", "packageCount", "deliveryDate", "pickupTime", "quotedAt", "instructions", "version"])
        self._action = "Create" if creation_state is EntityCreationState.RESERVED else "Update"
        self._comment = None
        self._loaded_fields = set(kwargs.keys())
        self.id = kwargs.get("id")

        self.platform = kwargs.get("platform")

        self.reference = kwargs.get("reference")

        self.amount = kwargs.get("amount")

        self.shipmentNumber = kwargs.get("shipmentNumber")

        self.packageCount = kwargs.get("packageCount")

        self.deliveryDate = kwargs.get("deliveryDate")

        self.pickupTime = kwargs.get("pickupTime")

        self.quotedAt = kwargs.get("quotedAt")

        self.instructions = kwargs.get("instructions")

        self.version = kwargs.get("version")

        if isinstance(self.platform, dict):
            self.platform = Platform._teaql_from_record(**self.platform)
        self._ledger_id = getattr(self, "id", None)
        key = self._teaql_entity_key()
        if self._action == "Create":
            self._entity_root.mark_as_new(key)
        elif getattr(self, "version", None) is not None:
            self._entity_root.set_original_version(key, int(self.version))
        LoadedScalarSnapshots.capture(self, self._teaql_snapshot_values(), origin=creation_state)

    def _teaql_snapshot_values(self):
        payload = {}
        if "id" in self._loaded_fields:
            payload["id"] = Value.I64(self.id)

        if "platform" in self._loaded_fields:
            payload["platform"] = Value.I64(getattr(self.platform, "id", self.platform))

        if "reference" in self._loaded_fields:
            payload["reference"] = Value.Text(self.reference)

        if "amount" in self._loaded_fields:
            payload["amount"] = Value.Decimal(self.amount)

        if "shipmentNumber" in self._loaded_fields:
            payload["shipment_number"] = Value.I64(self.shipmentNumber)

        if "packageCount" in self._loaded_fields:
            payload["package_count"] = Value.I64(self.packageCount)

        if "deliveryDate" in self._loaded_fields:
            payload["delivery_date"] = Value.Date(self.deliveryDate)

        if "pickupTime" in self._loaded_fields:
            payload["pickup_time"] = Value.Time(self.pickupTime)

        if "quotedAt" in self._loaded_fields:
            payload["quoted_at"] = Value.DateTime(self.quotedAt)

        if "instructions" in self._loaded_fields:
            payload["instructions"] = Value.Text(self.instructions)

        if "version" in self._loaded_fields:
            payload["version"] = Value.I64(self.version)

        return payload

    def _teaql_entity_key(self):
        return EntityKey("FreightQuote", self._ledger_id)

    def _teaql_restore_fixed_values(self, values):
        """Runtime-owned restoration supplies only known, equal scalar values."""
        if "reference" in values:
            value = values["reference"]
            raw = value.val if isinstance(value, Value) else value
            self.reference = raw

        if "amount" in values:
            value = values["amount"]
            raw = value.val if isinstance(value, Value) else value
            self.amount = raw

        if "shipment_number" in values:
            value = values["shipment_number"]
            raw = value.val if isinstance(value, Value) else value
            self.shipmentNumber = raw

        if "package_count" in values:
            value = values["package_count"]
            raw = value.val if isinstance(value, Value) else value
            self.packageCount = raw

        if "delivery_date" in values:
            value = values["delivery_date"]
            raw = value.val if isinstance(value, Value) else value
            self.deliveryDate = raw

        if "pickup_time" in values:
            value = values["pickup_time"]
            raw = value.val if isinstance(value, Value) else value
            self.pickupTime = raw

        if "quoted_at" in values:
            value = values["quoted_at"]
            raw = value.val if isinstance(value, Value) else value
            self.quotedAt = raw

        if "instructions" in values:
            value = values["instructions"]
            raw = value.val if isinstance(value, Value) else value
            self.instructions = raw


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
        context._validate_generated_graph_input("FreightQuote",
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
            context._validate_mutation_fields("FreightQuote", ledger)
            if self._action == "Update":
                if "id" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("id"), message="Mutation requires a fully loaded entity", entity_type="FreightQuote")])
                if "platform" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("platform"), message="Mutation requires a fully loaded entity", entity_type="FreightQuote")])
                if "reference" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("reference"), message="Mutation requires a fully loaded entity", entity_type="FreightQuote")])
                if "amount" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("amount"), message="Mutation requires a fully loaded entity", entity_type="FreightQuote")])
                if "shipmentNumber" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("shipment_number"), message="Mutation requires a fully loaded entity", entity_type="FreightQuote")])
                if "packageCount" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("package_count"), message="Mutation requires a fully loaded entity", entity_type="FreightQuote")])
                if "deliveryDate" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("delivery_date"), message="Mutation requires a fully loaded entity", entity_type="FreightQuote")])
                if "pickupTime" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("pickup_time"), message="Mutation requires a fully loaded entity", entity_type="FreightQuote")])
                if "quotedAt" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("quoted_at"), message="Mutation requires a fully loaded entity", entity_type="FreightQuote")])
                if "instructions" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("instructions"), message="Mutation requires a fully loaded entity", entity_type="FreightQuote")])
                if "version" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("version"), message="Mutation requires a fully loaded entity", entity_type="FreightQuote")])
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
            context._validate_mutation_fields("FreightQuote", ledger)
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

        if "platform" in self._loaded_fields:
            reference = self.platform
            reference_id = getattr(reference, "id", reference)
            payload["platform"] = (Value.Object(reference)
                if reference is not None and hasattr(reference, "id") and reference_id is None
                else Value.I64(reference_id))

        if "reference" in self._loaded_fields:
            payload["reference"] = Value.Text(self.reference)

        if "amount" in self._loaded_fields:
            payload["amount"] = Value.Decimal(self.amount)

        if "shipmentNumber" in self._loaded_fields:
            payload["shipment_number"] = Value.I64(self.shipmentNumber)

        if "packageCount" in self._loaded_fields:
            payload["package_count"] = Value.I64(self.packageCount)

        if "deliveryDate" in self._loaded_fields:
            payload["delivery_date"] = Value.Date(self.deliveryDate)

        if "pickupTime" in self._loaded_fields:
            payload["pickup_time"] = Value.Time(self.pickupTime)

        if "quotedAt" in self._loaded_fields:
            payload["quoted_at"] = Value.DateTime(self.quotedAt)

        if "instructions" in self._loaded_fields:
            payload["instructions"] = Value.Text(self.instructions)

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
            cmd = InsertCommand("FreightQuote", payload)
        elif action == "Update":
            original_version = self._entity_root.original_version(self._teaql_entity_key())
            cmd = UpdateCommand("FreightQuote", Value.from_any(getattr(self, "id", None)),
                original_version if original_version is not None else getattr(self, "version", None))
            for key, value in payload.items():
                if key not in ("id", "version"): cmd.value(key, value)
        else:
            original_version = self._entity_root.original_version(self._teaql_entity_key())
            cmd = DeleteCommand("FreightQuote", Value.from_any(getattr(self, "id", None)),
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
        session.capture_loaded_values("FreightQuote", LoadedScalarSnapshots.values(self))
        if self._entity_root.has_pending(self._teaql_entity_key()):
            if self._action == "Update":
                if "id" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("id"), message="Mutation requires a fully loaded entity", entity_type="FreightQuote")])
                if "platform" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("platform"), message="Mutation requires a fully loaded entity", entity_type="FreightQuote")])
                if "reference" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("reference"), message="Mutation requires a fully loaded entity", entity_type="FreightQuote")])
                if "amount" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("amount"), message="Mutation requires a fully loaded entity", entity_type="FreightQuote")])
                if "shipmentNumber" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("shipment_number"), message="Mutation requires a fully loaded entity", entity_type="FreightQuote")])
                if "packageCount" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("package_count"), message="Mutation requires a fully loaded entity", entity_type="FreightQuote")])
                if "deliveryDate" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("delivery_date"), message="Mutation requires a fully loaded entity", entity_type="FreightQuote")])
                if "pickupTime" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("pickup_time"), message="Mutation requires a fully loaded entity", entity_type="FreightQuote")])
                if "quotedAt" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("quoted_at"), message="Mutation requires a fully loaded entity", entity_type="FreightQuote")])
                if "instructions" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("instructions"), message="Mutation requires a fully loaded entity", entity_type="FreightQuote")])
                if "version" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("version"), message="Mutation requires a fully loaded entity", entity_type="FreightQuote")])
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
                "Mutation provider did not return authoritative persisted state for FreightQuote"
            )
        rollback_payload = {field: getattr(self, field, None) for field in self._loaded_fields | {"id", "version"}}
        rollback_snapshot = LoadedScalarSnapshots.values(self)
        rollback_origin = LoadedScalarSnapshots.origin(self)
        rollback_creation_state = self._creation_state
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
        if "platform" in persisted:
            self.platform = persisted["platform"]
            self._loaded_fields.add("platform")
        elif "platform" in persisted:
            self.platform = persisted["platform"]
            self._loaded_fields.add("platform")
        if "reference" in persisted:
            self.reference = persisted["reference"]
            self._loaded_fields.add("reference")
        elif "reference" in persisted:
            self.reference = persisted["reference"]
            self._loaded_fields.add("reference")
        if "amount" in persisted:
            self.amount = persisted["amount"]
            self._loaded_fields.add("amount")
        elif "amount" in persisted:
            self.amount = persisted["amount"]
            self._loaded_fields.add("amount")
        if "shipment_number" in persisted:
            self.shipmentNumber = persisted["shipment_number"]
            self._loaded_fields.add("shipmentNumber")
        elif "shipmentNumber" in persisted:
            self.shipmentNumber = persisted["shipmentNumber"]
            self._loaded_fields.add("shipmentNumber")
        if "package_count" in persisted:
            self.packageCount = persisted["package_count"]
            self._loaded_fields.add("packageCount")
        elif "packageCount" in persisted:
            self.packageCount = persisted["packageCount"]
            self._loaded_fields.add("packageCount")
        if "delivery_date" in persisted:
            self.deliveryDate = persisted["delivery_date"]
            self._loaded_fields.add("deliveryDate")
        elif "deliveryDate" in persisted:
            self.deliveryDate = persisted["deliveryDate"]
            self._loaded_fields.add("deliveryDate")
        if "pickup_time" in persisted:
            self.pickupTime = persisted["pickup_time"]
            self._loaded_fields.add("pickupTime")
        elif "pickupTime" in persisted:
            self.pickupTime = persisted["pickupTime"]
            self._loaded_fields.add("pickupTime")
        if "quoted_at" in persisted:
            self.quotedAt = persisted["quoted_at"]
            self._loaded_fields.add("quotedAt")
        elif "quotedAt" in persisted:
            self.quotedAt = persisted["quotedAt"]
            self._loaded_fields.add("quotedAt")
        if "instructions" in persisted:
            self.instructions = persisted["instructions"]
            self._loaded_fields.add("instructions")
        elif "instructions" in persisted:
            self.instructions = persisted["instructions"]
            self._loaded_fields.add("instructions")
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
        if "id" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.id, value):
            return self
        self.id = value
        self._loaded_fields.add("id")
        self._entity_root.set(self._teaql_entity_key(), "id", Value.from_any(value))
        return self

    def update_reference(self, value):
        if "reference" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.reference, value):
            return self
        self.reference = value
        self._loaded_fields.add("reference")
        self._entity_root.set(self._teaql_entity_key(), "reference", Value.from_any(value))
        return self

    def update_amount(self, value):
        if "amount" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.amount, value):
            return self
        self.amount = value
        self._loaded_fields.add("amount")
        self._entity_root.set(self._teaql_entity_key(), "amount", Value.from_any(value))
        return self

    def update_shipment_number(self, value):
        if "shipmentNumber" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.shipmentNumber, value):
            return self
        self.shipmentNumber = value
        self._loaded_fields.add("shipmentNumber")
        self._entity_root.set(self._teaql_entity_key(), "shipment_number", Value.from_any(value))
        return self

    def update_package_count(self, value):
        if "packageCount" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.packageCount, value):
            return self
        self.packageCount = value
        self._loaded_fields.add("packageCount")
        self._entity_root.set(self._teaql_entity_key(), "package_count", Value.from_any(value))
        return self

    def update_delivery_date(self, value):
        if "deliveryDate" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.deliveryDate, value):
            return self
        self.deliveryDate = value
        self._loaded_fields.add("deliveryDate")
        self._entity_root.set(self._teaql_entity_key(), "delivery_date", Value.from_any(value))
        return self

    def update_pickup_time(self, value):
        if "pickupTime" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.pickupTime, value):
            return self
        self.pickupTime = value
        self._loaded_fields.add("pickupTime")
        self._entity_root.set(self._teaql_entity_key(), "pickup_time", Value.from_any(value))
        return self

    def update_quoted_at(self, value):
        if "quotedAt" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.quotedAt, value):
            return self
        self.quotedAt = value
        self._loaded_fields.add("quotedAt")
        self._entity_root.set(self._teaql_entity_key(), "quoted_at", Value.from_any(value))
        return self

    def update_instructions(self, value):
        if "instructions" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.instructions, value):
            return self
        self.instructions = value
        self._loaded_fields.add("instructions")
        self._entity_root.set(self._teaql_entity_key(), "instructions", Value.from_any(value))
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
