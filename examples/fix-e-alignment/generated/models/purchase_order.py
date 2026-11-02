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
from models.tenant import Tenant


class PurchaseOrder:
    _teaql_json_schema = EntityJSONSchema("PurchaseOrder", (
        EntityJSONField("id", "id", "id"),
        EntityJSONField("tenant", "tenant", "reference", factory=lambda: Tenant),
        EntityJSONField("contact_phone", "contactPhone", "text"),
        EntityJSONField("internal_note", "internalNote", "text"),
        EntityJSONField("create_time", "createTime", "datetime"),
        EntityJSONField("update_time", "updateTime", "datetime"),
        EntityJSONField("version", "version", "version"),
        EntityJSONField("order_item_list", "_order_item_list", "many", factory=lambda: getattr(import_module("models.order_item"), "OrderItem"), loaded_name="order_item_list")
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
        if "tenant" in kwargs and "tenant" not in kwargs:
            kwargs["tenant"] = kwargs.pop("tenant")
        if "contact_phone" in kwargs and "contactPhone" not in kwargs:
            kwargs["contactPhone"] = kwargs.pop("contact_phone")
        if "internal_note" in kwargs and "internalNote" not in kwargs:
            kwargs["internalNote"] = kwargs.pop("internal_note")
        if "create_time" in kwargs and "createTime" not in kwargs:
            kwargs["createTime"] = kwargs.pop("create_time")
        if "update_time" in kwargs and "updateTime" not in kwargs:
            kwargs["updateTime"] = kwargs.pop("update_time")
        if "version" in kwargs and "version" not in kwargs:
            kwargs["version"] = kwargs.pop("version")
        self._projection_properties = ProjectionProperties(kwargs,
            ["id", "tenant", "contactPhone", "internalNote", "createTime", "updateTime", "version", "order_item_list"])
        self._action = "Update" if kwargs.get("id") else "Create"
        self._comment = None
        self._loaded_fields = set(kwargs.keys())
        self.id = kwargs.get("id")

        self.tenant = kwargs.get("tenant")

        self.contactPhone = kwargs.get("contactPhone")

        self.internalNote = kwargs.get("internalNote")

        self.createTime = kwargs.get("createTime")

        self.updateTime = kwargs.get("updateTime")

        self.version = kwargs.get("version")

        if isinstance(self.tenant, dict):
            self.tenant = Tenant(**self.tenant)
        self._order_item_list = kwargs.get("order_item_list", [])
        if "order_item_list" in kwargs or kwargs.get("id") is None:
            self._loaded_fields.add("order_item_list")
        if self._order_item_list:
            from models.order_item import OrderItem
            source = self._order_item_list
            hydrated = [
                item if isinstance(item, OrderItem) else OrderItem(_entity_root=self._entity_root, **item)
                for item in source
            ]
            self._order_item_list = (SmartList(hydrated, facets=source.facets, total_count=source.total_count)
                if isinstance(source, SmartList) else hydrated)
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

        if "tenant" in self._loaded_fields:
            payload["tenant"] = Value.I64(getattr(self.tenant, "id", self.tenant))

        if "contactPhone" in self._loaded_fields:
            payload["contact_phone"] = Value.Text(self.contactPhone)

        if "internalNote" in self._loaded_fields:
            payload["internal_note"] = Value.Text(self.internalNote)

        if "createTime" in self._loaded_fields:
            payload["create_time"] = Value.DateTime(self.createTime)

        if "updateTime" in self._loaded_fields:
            payload["update_time"] = Value.DateTime(self.updateTime)

        if "version" in self._loaded_fields:
            payload["version"] = Value.I64(self.version)

        return payload

    def _teaql_entity_key(self):
        return EntityKey("PurchaseOrder", self._ledger_id)

    def get_dynamic_property(self, name):
        return self._projection_properties.get(name)

    def _teaql_attach_root(self, root):
        if self._entity_root is not root:
            root.merge_entity_from(self._entity_root, self._teaql_entity_key())
            self._entity_root = root
        for child in self._order_item_list:
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
            context._validate_mutation_fields("PurchaseOrder", ledger)
            if self._action == "Update":
                if "id" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("id"), message="Mutation requires a fully loaded entity", entity_type="PurchaseOrder")])
                if "tenant" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("tenant"), message="Mutation requires a fully loaded entity", entity_type="PurchaseOrder")])
                if "contactPhone" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("contact_phone"), message="Mutation requires a fully loaded entity", entity_type="PurchaseOrder")])
                if "internalNote" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("internal_note"), message="Mutation requires a fully loaded entity", entity_type="PurchaseOrder")])
                if "createTime" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("create_time"), message="Mutation requires a fully loaded entity", entity_type="PurchaseOrder")])
                if "updateTime" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("update_time"), message="Mutation requires a fully loaded entity", entity_type="PurchaseOrder")])
                if "version" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("version"), message="Mutation requires a fully loaded entity", entity_type="PurchaseOrder")])
            self._teaql_validate_context_root(context, ledger)
            # Required business values may be supplied by customer Fix. Root,
            # canonical-key, version and completeness admission still runs first.
            if validate_required:
                _action, command = self._teaql_build_command()
                context._validate_required_mutation_input(command, parent_field=parent_field)
        for index, child in enumerate(self._order_item_list):
            try:
                child._teaql_validate_input_graph(context, visited, "purchase_order", validate_required=validate_required)
            except CheckException as error:
                prefix = ObjectLocation().property("order_item_list").index(index)
                raise CheckException([
                    v.prefixed_by(prefix)
                    for v in error.violations
                ]) from error

    def _teaql_validate_context_root(self, context, pending):
        context._validate_context_root_input(
            "PurchaseOrder", "tenant",
            "Tenant", self._action,
            LoadedScalarSnapshots.values(self), self._teaql_scalar_payload(), pending)


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
            self.id = int(await allocator("PurchaseOrder"))
            self._loaded_fields.add("id")
            self._ledger_id = self.id
            new_key = self._teaql_entity_key()
            self._entity_root.rekey(old_key, new_key)
            self._entity_root.set(new_key, "id", Value.I64(self.id))
        await self._teaql_ensure_business_ids(context)
        for child in self._order_item_list:
            child._teaql_attach_root(self._entity_root)
            await child._teaql_reserve_graph_ids(context, visited)

    async def _teaql_prepare_graph(self, context, session):
        # Complete all input/Fix checks before reserving any graph identity.
        # Stable IDs then make the final policy plan and TraceScope concrete.
        self._teaql_validate_input_graph(context, set())
        self._teaql_prepare_input_graph(context, set())
        # Fix may edit a sibling or its version; re-admit the whole graph before IDs.
        self._teaql_validate_input_graph(context, set(), validate_required=True)
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
            context._validate_mutation_fields("PurchaseOrder", ledger)
            _action, cmd = self._teaql_build_command()
            try:
                context._check_and_fix_mutation_input(cmd, deferred_fields=())
            finally:
                for field, value in getattr(cmd, "values", {}).items():
                    if field not in ("id", "version"):
                        self._entity_root.set(self._teaql_entity_key(), field, value)
        for index, child in enumerate(self._order_item_list):
            child._teaql_attach_root(self._entity_root)
            # The object reference exists even before either endpoint has a stable ID.
            # Do not confuse two absent IDs with an already-established association.
            if getattr(child, "purchaseOrder", None) is not self:
                child.update_purchase_order(self)
            try:
                child._teaql_prepare_input_graph(context, visited)
            except CheckException as error:
                prefix = ObjectLocation().property("order_item_list").index(index)
                raise CheckException([
                    v.prefixed_by(prefix)
                    for v in error.violations
                ]) from error

    def _teaql_scalar_payload(self):
        payload = {}
        if "id" in self._loaded_fields:
            payload["id"] = Value.I64(self.id)

        if "tenant" in self._loaded_fields:
            reference = self.tenant
            reference_id = getattr(reference, "id", reference)
            payload["tenant"] = (Value.Object(reference)
                if reference is not None and hasattr(reference, "id") and reference_id is None
                else Value.I64(reference_id))

        if "contactPhone" in self._loaded_fields:
            payload["contact_phone"] = Value.Text(self.contactPhone)

        if "internalNote" in self._loaded_fields:
            payload["internal_note"] = Value.Text(self.internalNote)

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
        if action == "Create":
            # Preparation Fix values live in the ledger until commit. Rebuilding
            # from entity attributes alone must not discard those checked values.
            ledger = dict(self._entity_root.current_change_set().changes()).get(self._teaql_entity_key(), {})
            payload.update({field: value for field, value in ledger.items() if field not in ("id", "version")})
        elif action == "Update":
            ledger = dict(self._entity_root.current_change_set().changes()).get(self._teaql_entity_key(), {})
            payload = {field: value for field, value in ledger.items() if field not in ("id", "version")}
        if "tenant" in payload:
            reference = payload["tenant"].val
            if reference is not None and hasattr(reference, "id") and reference.id is not None:
                payload["tenant"] = Value.I64(reference.id)
        if action == "Create":
            cmd = InsertCommand("PurchaseOrder", payload)
        elif action == "Update":
            original_version = self._entity_root.original_version(self._teaql_entity_key())
            cmd = UpdateCommand("PurchaseOrder", Value.from_any(getattr(self, "id", None)),
                original_version if original_version is not None else getattr(self, "version", None))
            for key, value in payload.items():
                if key not in ("id", "version"): cmd.value(key, value)
        else:
            original_version = self._entity_root.original_version(self._teaql_entity_key())
            cmd = DeleteCommand("PurchaseOrder", Value.from_any(getattr(self, "id", None)),
                original_version if original_version is not None else getattr(self, "version", None))
        if action != "Create":
            cmd.old_values = LoadedScalarSnapshots.values(self)
        return action, cmd

    def _teaql_preflight_graph(self, context, session, parent=None):
        if parent is None:
            MutationIntent(self._comment)
        scope = session.scope(self._teaql_entity_key(), parent, self._comment)
        session.capture_loaded_values("PurchaseOrder", LoadedScalarSnapshots.values(self))
        if self._entity_root.has_pending(self._teaql_entity_key()):
            if self._action == "Update":
                if "id" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("id"), message="Mutation requires a fully loaded entity", entity_type="PurchaseOrder")])
                if "tenant" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("tenant"), message="Mutation requires a fully loaded entity", entity_type="PurchaseOrder")])
                if "contactPhone" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("contact_phone"), message="Mutation requires a fully loaded entity", entity_type="PurchaseOrder")])
                if "internalNote" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("internal_note"), message="Mutation requires a fully loaded entity", entity_type="PurchaseOrder")])
                if "createTime" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("create_time"), message="Mutation requires a fully loaded entity", entity_type="PurchaseOrder")])
                if "updateTime" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("update_time"), message="Mutation requires a fully loaded entity", entity_type="PurchaseOrder")])
                if "version" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("version"), message="Mutation requires a fully loaded entity", entity_type="PurchaseOrder")])
            action, cmd = self._teaql_build_command()
            try:
                context.preflight_mutation(cmd)
                self._teaql_validate_context_root(context, getattr(cmd, "values", {}))
            finally:
                for field, value in getattr(cmd, "values", {}).items():
                    if field not in ("id", "version"):
                        self._entity_root.set(self._teaql_entity_key(), field, value)
            session._remember_prepared_mutation(self, action, cmd)
        for index, child in enumerate(self._order_item_list):
            child._teaql_attach_root(self._entity_root)
            current = getattr(child, "purchaseOrder", None)
            if getattr(current, "id", current) != self.id:
                child.update_purchase_order(self)
            try:
                child._teaql_preflight_graph(context, session, scope)
            except CheckException as error:
                prefix = ObjectLocation().property("order_item_list").index(index)
                raise CheckException([
                    v.prefixed_by(prefix)
                    for v in error.violations
                ]) from error

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
                "Mutation provider did not return authoritative persisted state for PurchaseOrder"
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
        if "tenant" in persisted:
            self.tenant = persisted["tenant"]
            self._loaded_fields.add("tenant")
        elif "tenant" in persisted:
            self.tenant = persisted["tenant"]
            self._loaded_fields.add("tenant")
        if "contact_phone" in persisted:
            self.contactPhone = persisted["contact_phone"]
            self._loaded_fields.add("contactPhone")
        elif "contactPhone" in persisted:
            self.contactPhone = persisted["contactPhone"]
            self._loaded_fields.add("contactPhone")
        if "internal_note" in persisted:
            self.internalNote = persisted["internal_note"]
            self._loaded_fields.add("internalNote")
        elif "internalNote" in persisted:
            self.internalNote = persisted["internalNote"]
            self._loaded_fields.add("internalNote")
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
        cascade_relations.append(("order_item_list", self._order_item_list, "update_purchase_order", "purchaseOrder"))
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

    def update_contact_phone(self, value):
        if "contactPhone" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.contactPhone, value):
            return self
        self.contactPhone = value
        self._loaded_fields.add("contactPhone")
        self._entity_root.set(self._teaql_entity_key(), "contact_phone", Value.from_any(value))
        return self

    def update_internal_note(self, value):
        if "internalNote" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.internalNote, value):
            return self
        self.internalNote = value
        self._loaded_fields.add("internalNote")
        self._entity_root.set(self._teaql_entity_key(), "internal_note", Value.from_any(value))
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
    def _teaql_set_tenant(self, value):
        assigned_id = getattr(value, "id", value) if value else None
        current = self.tenant
        current_id = getattr(current, "id", current)
        if "tenant" in self._loaded_fields and LoadedScalarSnapshots.same_value(current_id, assigned_id) and (assigned_id is not None or current is value):
            return self
        self.tenant = value if value is not None and hasattr(value, "id") and assigned_id is None else assigned_id
        self._loaded_fields.add("tenant")
        self._entity_root.set(self._teaql_entity_key(), "tenant",
            Value.Object(self.tenant) if self.tenant is not None and hasattr(self.tenant, "id")
            else Value.from_any(self.tenant))
        return self

    def order_item_list(self) -> list:
        self._loaded_fields.add("order_item_list")
        return self._order_item_list
