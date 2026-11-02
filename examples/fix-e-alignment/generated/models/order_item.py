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
from models.purchase_order import PurchaseOrder
from models.tenant import Tenant


class OrderItem:
    _teaql_json_schema = EntityJSONSchema("OrderItem", (
        EntityJSONField("id", "id", "id"),
        EntityJSONField("purchase_order", "purchaseOrder", "reference", factory=lambda: PurchaseOrder),
        EntityJSONField("tenant", "tenant", "reference", factory=lambda: Tenant),
        EntityJSONField("product_name", "productName", "text"),
        EntityJSONField("unit_price", "unitPrice", "decimal"),
        EntityJSONField("create_time", "createTime", "datetime"),
        EntityJSONField("update_time", "updateTime", "datetime"),
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
        if "purchase_order" in kwargs and "purchaseOrder" not in kwargs:
            kwargs["purchaseOrder"] = kwargs.pop("purchase_order")
        if "tenant" in kwargs and "tenant" not in kwargs:
            kwargs["tenant"] = kwargs.pop("tenant")
        if "product_name" in kwargs and "productName" not in kwargs:
            kwargs["productName"] = kwargs.pop("product_name")
        if "unit_price" in kwargs and "unitPrice" not in kwargs:
            kwargs["unitPrice"] = kwargs.pop("unit_price")
        if "create_time" in kwargs and "createTime" not in kwargs:
            kwargs["createTime"] = kwargs.pop("create_time")
        if "update_time" in kwargs and "updateTime" not in kwargs:
            kwargs["updateTime"] = kwargs.pop("update_time")
        if "version" in kwargs and "version" not in kwargs:
            kwargs["version"] = kwargs.pop("version")
        self._projection_properties = ProjectionProperties(kwargs,
            ["id", "purchaseOrder", "tenant", "productName", "unitPrice", "createTime", "updateTime", "version"])
        self._action = "Update" if kwargs.get("id") else "Create"
        self._comment = None
        self._loaded_fields = set(kwargs.keys())
        self.id = kwargs.get("id")

        self.purchaseOrder = kwargs.get("purchaseOrder")

        self.tenant = kwargs.get("tenant")

        self.productName = kwargs.get("productName")

        self.unitPrice = kwargs.get("unitPrice")

        self.createTime = kwargs.get("createTime")

        self.updateTime = kwargs.get("updateTime")

        self.version = kwargs.get("version")

        if isinstance(self.purchaseOrder, dict):
            self.purchaseOrder = PurchaseOrder(**self.purchaseOrder)
        if isinstance(self.tenant, dict):
            self.tenant = Tenant(**self.tenant)
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

        if "purchaseOrder" in self._loaded_fields:
            payload["purchase_order"] = Value.I64(getattr(self.purchaseOrder, "id", self.purchaseOrder))

        if "tenant" in self._loaded_fields:
            payload["tenant"] = Value.I64(getattr(self.tenant, "id", self.tenant))

        if "productName" in self._loaded_fields:
            payload["product_name"] = Value.Text(self.productName)

        if "unitPrice" in self._loaded_fields:
            payload["unit_price"] = Value.Decimal(self.unitPrice)

        if "createTime" in self._loaded_fields:
            payload["create_time"] = Value.DateTime(self.createTime)

        if "updateTime" in self._loaded_fields:
            payload["update_time"] = Value.DateTime(self.updateTime)

        if "version" in self._loaded_fields:
            payload["version"] = Value.I64(self.version)

        return payload

    def _teaql_entity_key(self):
        return EntityKey("OrderItem", self._ledger_id)

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
            context._validate_mutation_fields("OrderItem", ledger)
            if self._action == "Update":
                if "id" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("id"), message="Mutation requires a fully loaded entity", entity_type="OrderItem")])
                if "purchaseOrder" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("purchase_order"), message="Mutation requires a fully loaded entity", entity_type="OrderItem")])
                if "tenant" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("tenant"), message="Mutation requires a fully loaded entity", entity_type="OrderItem")])
                if "productName" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("product_name"), message="Mutation requires a fully loaded entity", entity_type="OrderItem")])
                if "unitPrice" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("unit_price"), message="Mutation requires a fully loaded entity", entity_type="OrderItem")])
                if "createTime" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("create_time"), message="Mutation requires a fully loaded entity", entity_type="OrderItem")])
                if "updateTime" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("update_time"), message="Mutation requires a fully loaded entity", entity_type="OrderItem")])
                if "version" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("version"), message="Mutation requires a fully loaded entity", entity_type="OrderItem")])
            self._teaql_validate_context_root(context, ledger)
            # Required business values may be supplied by customer Fix. Root,
            # canonical-key, version and completeness admission still runs first.
            if validate_required:
                _action, command = self._teaql_build_command()
                context._validate_required_mutation_input(command, parent_field=parent_field)

    def _teaql_validate_context_root(self, context, pending):
        context._validate_context_root_input(
            "OrderItem", "tenant",
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
            self.id = int(await allocator("OrderItem"))
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
            context._validate_mutation_fields("OrderItem", ledger)
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

        if "purchaseOrder" in self._loaded_fields:
            reference = self.purchaseOrder
            reference_id = getattr(reference, "id", reference)
            payload["purchase_order"] = (Value.Object(reference)
                if reference is not None and hasattr(reference, "id") and reference_id is None
                else Value.I64(reference_id))

        if "tenant" in self._loaded_fields:
            reference = self.tenant
            reference_id = getattr(reference, "id", reference)
            payload["tenant"] = (Value.Object(reference)
                if reference is not None and hasattr(reference, "id") and reference_id is None
                else Value.I64(reference_id))

        if "productName" in self._loaded_fields:
            payload["product_name"] = Value.Text(self.productName)

        if "unitPrice" in self._loaded_fields:
            payload["unit_price"] = Value.Decimal(self.unitPrice)

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
        if "purchase_order" in payload:
            reference = payload["purchase_order"].val
            if reference is not None and hasattr(reference, "id") and reference.id is not None:
                payload["purchase_order"] = Value.I64(reference.id)
        if "tenant" in payload:
            reference = payload["tenant"].val
            if reference is not None and hasattr(reference, "id") and reference.id is not None:
                payload["tenant"] = Value.I64(reference.id)
        if action == "Create":
            cmd = InsertCommand("OrderItem", payload)
        elif action == "Update":
            original_version = self._entity_root.original_version(self._teaql_entity_key())
            cmd = UpdateCommand("OrderItem", Value.from_any(getattr(self, "id", None)),
                original_version if original_version is not None else getattr(self, "version", None))
            for key, value in payload.items():
                if key not in ("id", "version"): cmd.value(key, value)
        else:
            original_version = self._entity_root.original_version(self._teaql_entity_key())
            cmd = DeleteCommand("OrderItem", Value.from_any(getattr(self, "id", None)),
                original_version if original_version is not None else getattr(self, "version", None))
        if action != "Create":
            cmd.old_values = LoadedScalarSnapshots.values(self)
        return action, cmd

    def _teaql_preflight_graph(self, context, session, parent=None):
        if parent is None:
            MutationIntent(self._comment)
        scope = session.scope(self._teaql_entity_key(), parent, self._comment)
        session.capture_loaded_values("OrderItem", LoadedScalarSnapshots.values(self))
        if self._entity_root.has_pending(self._teaql_entity_key()):
            if self._action == "Update":
                if "id" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("id"), message="Mutation requires a fully loaded entity", entity_type="OrderItem")])
                if "purchaseOrder" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("purchase_order"), message="Mutation requires a fully loaded entity", entity_type="OrderItem")])
                if "tenant" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("tenant"), message="Mutation requires a fully loaded entity", entity_type="OrderItem")])
                if "productName" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("product_name"), message="Mutation requires a fully loaded entity", entity_type="OrderItem")])
                if "unitPrice" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("unit_price"), message="Mutation requires a fully loaded entity", entity_type="OrderItem")])
                if "createTime" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("create_time"), message="Mutation requires a fully loaded entity", entity_type="OrderItem")])
                if "updateTime" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("update_time"), message="Mutation requires a fully loaded entity", entity_type="OrderItem")])
                if "version" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("version"), message="Mutation requires a fully loaded entity", entity_type="OrderItem")])
            action, cmd = self._teaql_build_command()
            try:
                context.preflight_mutation(cmd)
                self._teaql_validate_context_root(context, getattr(cmd, "values", {}))
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
                "Mutation provider did not return authoritative persisted state for OrderItem"
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
        if "purchase_order" in persisted:
            self.purchaseOrder = persisted["purchase_order"]
            self._loaded_fields.add("purchaseOrder")
        elif "purchaseOrder" in persisted:
            self.purchaseOrder = persisted["purchaseOrder"]
            self._loaded_fields.add("purchaseOrder")
        if "tenant" in persisted:
            self.tenant = persisted["tenant"]
            self._loaded_fields.add("tenant")
        elif "tenant" in persisted:
            self.tenant = persisted["tenant"]
            self._loaded_fields.add("tenant")
        if "product_name" in persisted:
            self.productName = persisted["product_name"]
            self._loaded_fields.add("productName")
        elif "productName" in persisted:
            self.productName = persisted["productName"]
            self._loaded_fields.add("productName")
        if "unit_price" in persisted:
            self.unitPrice = persisted["unit_price"]
            self._loaded_fields.add("unitPrice")
        elif "unitPrice" in persisted:
            self.unitPrice = persisted["unitPrice"]
            self._loaded_fields.add("unitPrice")
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

    def update_product_name(self, value):
        if "productName" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.productName, value):
            return self
        self.productName = value
        self._loaded_fields.add("productName")
        self._entity_root.set(self._teaql_entity_key(), "product_name", Value.from_any(value))
        return self

    def update_unit_price(self, value):
        if "unitPrice" in self._loaded_fields and LoadedScalarSnapshots.same_value(self.unitPrice, value):
            return self
        self.unitPrice = value
        self._loaded_fields.add("unitPrice")
        self._entity_root.set(self._teaql_entity_key(), "unit_price", Value.from_any(value))
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
    def update_purchase_order(self, value):
        assigned_id = getattr(value, "id", value) if value else None
        current = self.purchaseOrder
        current_id = getattr(current, "id", current)
        if "purchaseOrder" in self._loaded_fields and LoadedScalarSnapshots.same_value(current_id, assigned_id) and (assigned_id is not None or current is value):
            return self
        self.purchaseOrder = value if value is not None and hasattr(value, "id") and assigned_id is None else assigned_id
        self._loaded_fields.add("purchaseOrder")
        self._entity_root.set(self._teaql_entity_key(), "purchase_order",
            Value.Object(self.purchaseOrder) if self.purchaseOrder is not None and hasattr(self.purchaseOrder, "id")
            else Value.from_any(self.purchaseOrder))
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
