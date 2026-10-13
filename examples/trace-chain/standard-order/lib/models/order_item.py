from teaql.core.mutation import InsertCommand, UpdateCommand, DeleteCommand, MutationRequest
from teaql.core.value import Value
from teaql.core.request_intent import MutationIntent
from teaql.core.projection_properties import ProjectionProperties
from teaql.runtime.loaded_scalar_snapshot import LoadedScalarSnapshots
from teaql.runtime import CheckException, CheckResult, EntityKey, EntityRoot, ObjectLocation
import itertools
from models.customer_order import CustomerOrder


class OrderItem:
    _teaql_temporary_ids = itertools.count(1)
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
        if "product_name" in kwargs and "productName" not in kwargs:
            kwargs["productName"] = kwargs.pop("product_name")
        if "quantity" in kwargs and "quantity" not in kwargs:
            kwargs["quantity"] = kwargs.pop("quantity")
        if "unit_price" in kwargs and "unitPrice" not in kwargs:
            kwargs["unitPrice"] = kwargs.pop("unit_price")
        if "version" in kwargs and "version" not in kwargs:
            kwargs["version"] = kwargs.pop("version")
        self._projection_properties = ProjectionProperties(kwargs,
            ["id", "customerOrder", "productName", "quantity", "unitPrice", "version"])
        self._action = "Update" if kwargs.get("id") else "Create"
        self._comment = None
        self._loaded_fields = set(kwargs.keys())
        self.id = kwargs.get("id")

        self.customerOrder = kwargs.get("customerOrder")

        self.productName = kwargs.get("productName")

        self.quantity = kwargs.get("quantity")

        self.unitPrice = kwargs.get("unitPrice")

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

        if "productName" in self._loaded_fields:
            payload["product_name"] = Value.Text(self.productName)

        if "quantity" in self._loaded_fields:
            payload["quantity"] = Value.I64(self.quantity)

        if "unitPrice" in self._loaded_fields:
            payload["unit_price"] = Value.Decimal(self.unitPrice)

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
        # Reserve stable internal IDs before the transaction and before policy
        # review. A relation to a new parent must have the same identity in the
        # reviewed graph plan and in the commands eventually sent to SQL.
        await self._teaql_reserve_graph_ids(context, set())
        await self._teaql_ensure_business_ids(context)
        return await context.execute_graph_save(
            lambda session: self._teaql_preflight_and_save(session.context, session), comment=self._comment)

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

    async def _teaql_preflight_and_save(self, context, session):
        self._teaql_preflight_graph(context, session)
        return await self._teaql_save_within_graph(context, session)

    def _teaql_build_command(self):
        payload = {}
        if "id" in self._loaded_fields:
            payload["id"] = Value.I64(self.id)

        if "customerOrder" in self._loaded_fields:
            reference = self.customerOrder
            reference_id = getattr(reference, "id", reference)
            payload["customer_order"] = (Value.Object(reference)
                if reference is not None and hasattr(reference, "id") and reference_id is None
                else Value.I64(reference_id))

        if "productName" in self._loaded_fields:
            payload["product_name"] = Value.Text(self.productName)

        if "quantity" in self._loaded_fields:
            payload["quantity"] = Value.I64(self.quantity)

        if "unitPrice" in self._loaded_fields:
            payload["unit_price"] = Value.Decimal(self.unitPrice)

        if "version" in self._loaded_fields:
            payload["version"] = Value.I64(self.version)

        action = self._action
        if action == "Update":
            ledger = dict(self._entity_root.current_change_set().changes()).get(self._teaql_entity_key(), {})
            payload = {field: value for field, value in ledger.items() if field not in ("id", "version")}
        if action == "Create":
            cmd = InsertCommand("OrderItem", payload)
        elif action == "Update":
            cmd = UpdateCommand("OrderItem", Value.from_any(getattr(self, "id", None)), getattr(self, "version", None))
            for key, value in payload.items():
                if key not in ("id", "version"): cmd.value(key, value)
        else:
            cmd = DeleteCommand("OrderItem", Value.from_any(getattr(self, "id", None)), getattr(self, "version", None))
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
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("id"), message="Mutation requires a fully loaded entity")])
                if "customerOrder" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("customer_order"), message="Mutation requires a fully loaded entity")])
                if "productName" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("product_name"), message="Mutation requires a fully loaded entity")])
                if "quantity" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("quantity"), message="Mutation requires a fully loaded entity")])
                if "unitPrice" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("unit_price"), message="Mutation requires a fully loaded entity")])
                if "version" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("version"), message="Mutation requires a fully loaded entity")])
            _action, cmd = self._teaql_build_command()
            try:
                context.preflight_mutation(cmd)
            finally:
                for field, value in getattr(cmd, "values", {}).items():
                    if field not in ("id", "version"):
                        self._entity_root.set(self._teaql_entity_key(), field, value)

    async def _teaql_save_within_graph(self, context, session, parent=None):
        if parent is None:
            MutationIntent(self._comment)

        self._teaql_attach_root(self._entity_root)
        scope = session.scope(self._teaql_entity_key(), parent, self._comment)
        if not self._entity_root.has_pending(self._teaql_entity_key()):
            await self._teaql_cascade_children(context, session, scope)
            return self
        action, cmd = self._teaql_build_command()


        req = session.request(cmd, scope, self._entity_root, self._teaql_entity_key())

        try:
            context.check_and_fix_mutation(cmd)
        finally:
            for field, value in getattr(cmd, "values", {}).items():
                if field not in ("id", "version"):
                    self._entity_root.set(self._teaql_entity_key(), field, value)
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
        if "customer_order" in persisted:
            self.customerOrder = persisted["customer_order"]
            self._loaded_fields.add("customerOrder")
        elif "customerOrder" in persisted:
            self.customerOrder = persisted["customerOrder"]
            self._loaded_fields.add("customerOrder")
        if "product_name" in persisted:
            self.productName = persisted["product_name"]
            self._loaded_fields.add("productName")
        elif "productName" in persisted:
            self.productName = persisted["productName"]
            self._loaded_fields.add("productName")
        if "quantity" in persisted:
            self.quantity = persisted["quantity"]
            self._loaded_fields.add("quantity")
        elif "quantity" in persisted:
            self.quantity = persisted["quantity"]
            self._loaded_fields.add("quantity")
        if "unit_price" in persisted:
            self.unitPrice = persisted["unit_price"]
            self._loaded_fields.add("unitPrice")
        elif "unitPrice" in persisted:
            self.unitPrice = persisted["unitPrice"]
            self._loaded_fields.add("unitPrice")
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
        for relation_name, children, updater in cascade_relations:
            for index, child in enumerate(children):
                child._teaql_attach_root(self._entity_root)
                getattr(child, updater)(self)
                try:
                    await child._teaql_save_within_graph(context, session, scope)
                except CheckException as error:
                    prefix = ObjectLocation().property(relation_name).index(index)
                    raise CheckException([
                        CheckResult(
                            violation.rule_id,
                            violation.location.prefixed_by(prefix),
                            violation.input_value,
                            violation.system_value,
                            violation.message,
                        )
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
        if "id" in self._loaded_fields and self.id == value:
            return self
        self.id = value
        self._loaded_fields.add("id")
        self._entity_root.set(self._teaql_entity_key(), "id", Value.from_any(value))
        return self

    def update_product_name(self, value):
        if "productName" in self._loaded_fields and self.productName == value:
            return self
        self.productName = value
        self._loaded_fields.add("productName")
        self._entity_root.set(self._teaql_entity_key(), "product_name", Value.from_any(value))
        return self

    def update_quantity(self, value):
        if "quantity" in self._loaded_fields and self.quantity == value:
            return self
        self.quantity = value
        self._loaded_fields.add("quantity")
        self._entity_root.set(self._teaql_entity_key(), "quantity", Value.from_any(value))
        return self

    def update_unit_price(self, value):
        if "unitPrice" in self._loaded_fields and self.unitPrice == value:
            return self
        self.unitPrice = value
        self._loaded_fields.add("unitPrice")
        self._entity_root.set(self._teaql_entity_key(), "unit_price", Value.from_any(value))
        return self

    def update_version(self, value):
        if "version" in self._loaded_fields and self.version == value:
            return self
        self.version = value
        self._loaded_fields.add("version")
        self._entity_root.set(self._teaql_entity_key(), "version", Value.from_any(value))
        return self
    def update_customer_order(self, value):
        assigned_id = getattr(value, "id", value) if value else None
        current_id = getattr(self.customerOrder, "id", self.customerOrder)
        if "customerOrder" in self._loaded_fields and current_id == assigned_id:
            return self
        self.customerOrder = getattr(value, "id", value) if value else None
        self._loaded_fields.add("customerOrder")
        self._entity_root.set(self._teaql_entity_key(), "customer_order", Value.from_any(self.customerOrder))
        return self
