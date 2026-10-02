from teaql.core.mutation import InsertCommand, UpdateCommand, DeleteCommand, MutationRequest
from teaql.core import MutationIntent
from teaql.core.value import Value
from teaql.runtime import CheckException, CheckResult, EntityKey, EntityRoot, ObjectLocation
import itertools
from models.platform import Platform


class CustomerOrder:
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
        if "platform" in kwargs and "platform" not in kwargs:
            kwargs["platform"] = kwargs.pop("platform")
        if "order_number" in kwargs and "orderNumber" not in kwargs:
            kwargs["orderNumber"] = kwargs.pop("order_number")
        if "description" in kwargs and "description" not in kwargs:
            kwargs["description"] = kwargs.pop("description")
        if "version" in kwargs and "version" not in kwargs:
            kwargs["version"] = kwargs.pop("version")
        self._action = "Update" if kwargs.get("id") else "Create"
        self._comment = None
        self._loaded_fields = set(kwargs.keys())
        self.id = kwargs.get("id")

        self.platform = kwargs.get("platform")

        self.orderNumber = kwargs.get("orderNumber")

        self.description = kwargs.get("description")

        self.version = kwargs.get("version")

        if isinstance(self.platform, dict):
            self.platform = Platform(**self.platform)
        self._order_item_list = kwargs.get("order_item_list", [])
        if "order_item_list" in kwargs or kwargs.get("id") is None:
            self._loaded_fields.add("order_item_list")
        self._payment_list = kwargs.get("payment_list", [])
        if "payment_list" in kwargs or kwargs.get("id") is None:
            self._loaded_fields.add("payment_list")
        self._shipment_list = kwargs.get("shipment_list", [])
        if "shipment_list" in kwargs or kwargs.get("id") is None:
            self._loaded_fields.add("shipment_list")
        if self._order_item_list:
            from models.order_item import OrderItem
            self._order_item_list = [
                item if isinstance(item, OrderItem) else OrderItem(_entity_root=self._entity_root, **item)
                for item in self._order_item_list
            ]
        if self._payment_list:
            from models.payment import Payment
            self._payment_list = [
                item if isinstance(item, Payment) else Payment(_entity_root=self._entity_root, **item)
                for item in self._payment_list
            ]
        if self._shipment_list:
            from models.shipment import Shipment
            self._shipment_list = [
                item if isinstance(item, Shipment) else Shipment(_entity_root=self._entity_root, **item)
                for item in self._shipment_list
            ]
        self._ledger_id = getattr(self, "id", None)
        if self._ledger_id is None:
            self._ledger_id = -next(self._teaql_temporary_ids)
        key = self._teaql_entity_key()
        if self._action == "Create":
            self._entity_root.mark_as_new(key)
        elif getattr(self, "version", None) is not None:
            self._entity_root.set_original_version(key, int(self.version))

    def _teaql_entity_key(self):
        return EntityKey("CustomerOrder", self._ledger_id)

    def _teaql_attach_root(self, root):
        key = self._teaql_entity_key()
        if self._entity_root is not root and self._entity_root.has_pending(key):
            root.merge_entity_from(self._entity_root, key)
            self._entity_root = root
        for child in self._order_item_list:
            child._teaql_attach_root(root)
        for child in self._payment_list:
            child._teaql_attach_root(root)
        for child in self._shipment_list:
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
        intent = MutationIntent(self._comment)
        return await context.execute_graph_save(self._teaql_preflight_and_save, comment=intent.comment)

    async def _teaql_ensure_business_ids(self, context):
        if self._action != "Create":
            return

    async def _teaql_reserve_graph_ids(self, graph, visited):
        context = graph.context
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
            old_loaded = set(self._loaded_fields)
            self.id = int(await allocator("CustomerOrder"))
            self._loaded_fields.add("id")
            self._ledger_id = self.id
            new_key = self._teaql_entity_key()
            self._entity_root.rekey(old_key, new_key)
            self._entity_root.set(new_key, "id", Value.I64(self.id))
            def rollback_reservation():
                self.id = None
                self._ledger_id = old_key.id
                self._loaded_fields = old_loaded
                self._entity_root.rekey(new_key, old_key)
                self._entity_root.set(old_key, "id", Value.from_any(None))
            graph.after_rollback(rollback_reservation)
        await self._teaql_ensure_business_ids(context)
        for child in self._order_item_list:
            child._teaql_attach_root(self._entity_root)
            await child._teaql_reserve_graph_ids(graph, visited)
        for child in self._payment_list:
            child._teaql_attach_root(self._entity_root)
            await child._teaql_reserve_graph_ids(graph, visited)
        for child in self._shipment_list:
            child._teaql_attach_root(self._entity_root)
            await child._teaql_reserve_graph_ids(graph, visited)

    async def _teaql_preflight_and_save(self, graph):
        await self._teaql_reserve_graph_ids(graph, set())
        self._teaql_preflight_graph(graph)
        return await self._teaql_save_within_graph(graph)

    def _teaql_build_command(self):
        payload = {}
        if "id" in self._loaded_fields:
            payload["id"] = Value.I64(self.id)

        if "platform" in self._loaded_fields:
            reference = self.platform
            reference_id = getattr(reference, "id", reference)
            payload["platform"] = (Value.Object(reference)
                if reference is not None and hasattr(reference, "id") and reference_id is None
                else Value.I64(reference_id))

        if "orderNumber" in self._loaded_fields:
            payload["order_number"] = Value.Text(self.orderNumber)

        if "description" in self._loaded_fields:
            payload["description"] = Value.Text(self.description)

        if "version" in self._loaded_fields:
            payload["version"] = Value.I64(self.version)

        action = self._action
        if action == "Update":
            ledger = dict(self._entity_root.current_change_set().changes()).get(self._teaql_entity_key(), {})
            payload = {field: value for field, value in ledger.items() if field not in ("id", "version")}
        if action == "Create":
            cmd = InsertCommand("CustomerOrder", payload)
        elif action == "Update":
            original_version = self._entity_root.original_version(self._teaql_entity_key())
            cmd = UpdateCommand("CustomerOrder", Value.from_any(getattr(self, "id", None)),
                original_version if original_version is not None else getattr(self, "version", None))
            for key, value in payload.items():
                if key not in ("id", "version"): cmd.value(key, value)
        else:
            original_version = self._entity_root.original_version(self._teaql_entity_key())
            cmd = DeleteCommand("CustomerOrder", Value.from_any(getattr(self, "id", None)),
                original_version if original_version is not None else getattr(self, "version", None))
        return action, cmd

    def _teaql_preflight_graph(self, graph):
        context = graph.context
        if self._action != "Update" or self._entity_root.has_pending(self._teaql_entity_key()):
            if self._action == "Update":
                if "id" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("id"), message="Mutation requires a fully loaded entity")])
                if "platform" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("platform"), message="Mutation requires a fully loaded entity")])
                if "orderNumber" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("order_number"), message="Mutation requires a fully loaded entity")])
                if "description" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("description"), message="Mutation requires a fully loaded entity")])
                if "version" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("version"), message="Mutation requires a fully loaded entity")])
            _action, cmd = self._teaql_build_command()
            try:
                context.preflight_mutation(cmd)
            finally:
                for field, value in getattr(cmd, "values", {}).items():
                    if field not in ("id", "version"):
                        self._entity_root.set(self._teaql_entity_key(), field, value)
        for index, child in enumerate(self._order_item_list):
            child._teaql_attach_root(self._entity_root)
            current = getattr(child, "customerOrder", None)
            if getattr(current, "id", current) != self.id:
                child.update_customer_order(self)
            try:
                child._teaql_preflight_graph(graph)
            except CheckException as error:
                prefix = ObjectLocation().property("order_item_list").index(index)
                raise CheckException([
                    CheckResult(v.rule_id, v.location.prefixed_by(prefix), v.input_value, v.system_value, v.message)
                    for v in error.violations
                ]) from error
        for index, child in enumerate(self._payment_list):
            child._teaql_attach_root(self._entity_root)
            current = getattr(child, "customerOrder", None)
            if getattr(current, "id", current) != self.id:
                child.update_customer_order(self)
            try:
                child._teaql_preflight_graph(graph)
            except CheckException as error:
                prefix = ObjectLocation().property("payment_list").index(index)
                raise CheckException([
                    CheckResult(v.rule_id, v.location.prefixed_by(prefix), v.input_value, v.system_value, v.message)
                    for v in error.violations
                ]) from error
        for index, child in enumerate(self._shipment_list):
            child._teaql_attach_root(self._entity_root)
            current = getattr(child, "customerOrder", None)
            if getattr(current, "id", current) != self.id:
                child.update_customer_order(self)
            try:
                child._teaql_preflight_graph(graph)
            except CheckException as error:
                prefix = ObjectLocation().property("shipment_list").index(index)
                raise CheckException([
                    CheckResult(v.rule_id, v.location.prefixed_by(prefix), v.input_value, v.system_value, v.message)
                    for v in error.violations
                ]) from error

    async def _teaql_save_within_graph(self, graph, parent_scope=None):
        context = graph.context
        scope = graph.scope(self._teaql_entity_key(), parent_scope, self._comment)

        if self._action == "Update" and not self._entity_root.has_pending(self._teaql_entity_key()):
            await self._teaql_save_children(graph, scope)
            return self

        self._teaql_attach_root(self._entity_root)
        action, cmd = self._teaql_build_command()


        req = graph.request(cmd, scope, self._entity_root, self._teaql_entity_key())

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
                "Mutation provider did not return authoritative persisted state for CustomerOrder"
            )
        rollback_payload = {field: getattr(self, field, None) for field in self._loaded_fields | {"id", "version"}}
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
        if "order_number" in persisted:
            self.orderNumber = persisted["order_number"]
            self._loaded_fields.add("orderNumber")
        elif "orderNumber" in persisted:
            self.orderNumber = persisted["orderNumber"]
            self._loaded_fields.add("orderNumber")
        if "description" in persisted:
            self.description = persisted["description"]
            self._loaded_fields.add("description")
        elif "description" in persisted:
            self.description = persisted["description"]
            self._loaded_fields.add("description")
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
            if old_key != new_key:
                self._entity_root.rekey(new_key, old_key)
        graph.after_rollback(rollback_entity)
        if action != "Delete":
            self._action = "Update"

        if action != "Delete":
            await self._teaql_save_children(graph, scope)
        def commit_entity():
            self._entity_root.clear_entity(new_key)
            if getattr(self, "version", None) is not None:
                self._entity_root.accept_committed_version(new_key, int(self.version))
        graph.after_commit(commit_entity)
        return self

    async def _teaql_save_children(self, graph, scope):
        cascade_relations = []
        cascade_relations.append(("order_item_list", self._order_item_list, "update_customer_order", "customerOrder"))
        cascade_relations.append(("payment_list", self._payment_list, "update_customer_order", "customerOrder"))
        cascade_relations.append(("shipment_list", self._shipment_list, "update_customer_order", "customerOrder"))
        for relation_name, children, updater, member in cascade_relations:
            for index, child in enumerate(children):
                child._teaql_attach_root(self._entity_root)
                current = getattr(child, member, None)
                if getattr(current, "id", current) != self.id:
                    getattr(child, updater)(self)
                try:
                    await child._teaql_save_within_graph(graph, scope)
                except CheckException as error:
                    prefix = ObjectLocation().property(relation_name).index(index)
                    raise CheckException([
                        CheckResult(v.rule_id, v.location.prefixed_by(prefix), v.input_value, v.system_value, v.message)
                        for v in error.violations
                    ]) from error

    def update_id(self, value):
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError("id must be a positive integer")
        old_key = self._teaql_entity_key()
        new_key = EntityKey(old_key.entity, value)
        self._entity_root.rekey(old_key, new_key)
        self._ledger_id = value
        self.id = value
        self._loaded_fields.add("id")
        self._entity_root.set(self._teaql_entity_key(), "id", Value.from_any(value))
        return self

    def update_order_number(self, value):
        self.orderNumber = value
        self._loaded_fields.add("orderNumber")
        self._entity_root.set(self._teaql_entity_key(), "order_number", Value.from_any(value))
        return self

    def update_description(self, value):
        self.description = value
        self._loaded_fields.add("description")
        self._entity_root.set(self._teaql_entity_key(), "description", Value.from_any(value))
        return self

    def update_version(self, value):
        self.version = value
        self._loaded_fields.add("version")
        self._entity_root.set(self._teaql_entity_key(), "version", Value.from_any(value))
        return self
    def update_platform(self, value):
        self.platform = getattr(value, "id", value) if value else None
        self._loaded_fields.add("platform")
        self._entity_root.set(self._teaql_entity_key(), "platform", Value.from_any(self.platform))
        return self

    def order_item_list(self) -> list:
        self._loaded_fields.add("order_item_list")
        return self._order_item_list

    def payment_list(self) -> list:
        self._loaded_fields.add("payment_list")
        return self._payment_list

    def shipment_list(self) -> list:
        self._loaded_fields.add("shipment_list")
        return self._shipment_list
