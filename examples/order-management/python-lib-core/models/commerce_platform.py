from teaql.core.mutation import InsertCommand, UpdateCommand, DeleteCommand, MutationRequest
from teaql.core.value import Value
from teaql.runtime import CheckException, CheckResult, EntityKey, EntityRoot, ObjectLocation
import itertools

class CommercePlatform:
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
        if "name" in kwargs and "name" not in kwargs:
            kwargs["name"] = kwargs.pop("name")
        if "create_time" in kwargs and "createTime" not in kwargs:
            kwargs["createTime"] = kwargs.pop("create_time")
        if "update_time" in kwargs and "updateTime" not in kwargs:
            kwargs["updateTime"] = kwargs.pop("update_time")
        if "version" in kwargs and "version" not in kwargs:
            kwargs["version"] = kwargs.pop("version")
        self._action = "Update" if kwargs.get("id") else "Create"
        self._comment = None
        self._loaded_fields = set(kwargs.keys())
        self.id = kwargs.get("id")
        self.name = kwargs.get("name")
        self.createTime = kwargs.get("createTime")
        self.updateTime = kwargs.get("updateTime")
        self.version = kwargs.get("version")
        self._customer_list = kwargs.get("customer_list", [])
        if "customer_list" in kwargs or kwargs.get("id") is None:
            self._loaded_fields.add("customer_list")
        self._order_status_list = kwargs.get("order_status_list", [])
        if "order_status_list" in kwargs or kwargs.get("id") is None:
            self._loaded_fields.add("order_status_list")
        self._customer_order_list = kwargs.get("customer_order_list", [])
        if "customer_order_list" in kwargs or kwargs.get("id") is None:
            self._loaded_fields.add("customer_order_list")
        self._product_list = kwargs.get("product_list", [])
        if "product_list" in kwargs or kwargs.get("id") is None:
            self._loaded_fields.add("product_list")
        self._order_line_list = kwargs.get("order_line_list", [])
        if "order_line_list" in kwargs or kwargs.get("id") is None:
            self._loaded_fields.add("order_line_list")
        self._order_search_preset_list = kwargs.get("order_search_preset_list", [])
        if "order_search_preset_list" in kwargs or kwargs.get("id") is None:
            self._loaded_fields.add("order_search_preset_list")
        if self._customer_list:
            from models.customer import Customer
            self._customer_list = [
                item if isinstance(item, Customer) else Customer(**item)
                for item in self._customer_list
            ]
        if self._order_status_list:
            from models.order_status import OrderStatus
            self._order_status_list = [
                item if isinstance(item, OrderStatus) else OrderStatus(**item)
                for item in self._order_status_list
            ]
        if self._customer_order_list:
            from models.customer_order import CustomerOrder
            self._customer_order_list = [
                item if isinstance(item, CustomerOrder) else CustomerOrder(**item)
                for item in self._customer_order_list
            ]
        if self._product_list:
            from models.product import Product
            self._product_list = [
                item if isinstance(item, Product) else Product(**item)
                for item in self._product_list
            ]
        if self._order_line_list:
            from models.order_line import OrderLine
            self._order_line_list = [
                item if isinstance(item, OrderLine) else OrderLine(**item)
                for item in self._order_line_list
            ]
        if self._order_search_preset_list:
            from models.order_search_preset import OrderSearchPreset
            self._order_search_preset_list = [
                item if isinstance(item, OrderSearchPreset) else OrderSearchPreset(**item)
                for item in self._order_search_preset_list
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
        return EntityKey("CommercePlatform", self._ledger_id)

    def _teaql_attach_root(self, root):
        if self._entity_root is not root:
            root.merge_from(self._entity_root)
            self._entity_root = root
        for child in self._customer_list:
            child._teaql_attach_root(root)
        for child in self._order_status_list:
            child._teaql_attach_root(root)
        for child in self._customer_order_list:
            child._teaql_attach_root(root)
        for child in self._product_list:
            child._teaql_attach_root(root)
        for child in self._order_line_list:
            child._teaql_attach_root(root)
        for child in self._order_search_preset_list:
            child._teaql_attach_root(root)
        return self
    def mark_for_deletion(self):
        self._action = "Delete"
        self._entity_root.mark_as_deleted(self._teaql_entity_key())
        return self

    def audit_as(self, comment: str):
        if not isinstance(comment, str) or not comment.strip():
            raise ValueError("Security audit failure: audit_as() requires a non-empty reason")
        self._comment = comment
        return self

    async def save(self, context):
        return await context.execute_graph_save(lambda: self._teaql_preflight_and_save(context))

    async def _teaql_preflight_and_save(self, context):
        self._teaql_preflight_graph(context)
        return await self._teaql_save_within_graph(context)

    def _teaql_build_command(self):
        payload = {}
        if "id" in self._loaded_fields:
            payload["id"] = Value.I64(self.id)
        if "name" in self._loaded_fields:
            payload["name"] = Value.Text(self.name)
        if "createTime" in self._loaded_fields:
            payload["create_time"] = Value.DateTime(self.createTime)
        if "updateTime" in self._loaded_fields:
            payload["update_time"] = Value.DateTime(self.updateTime)
        if "version" in self._loaded_fields:
            payload["version"] = Value.I64(self.version)
        action = self._action
        if action == "Update":
            ledger = dict(self._entity_root.current_change_set().changes()).get(self._teaql_entity_key(), {})
            payload = {field: value for field, value in ledger.items() if field not in ("id", "version")}
        if action == "Create":
            cmd = InsertCommand("CommercePlatform", payload)
        elif action == "Update":
            cmd = UpdateCommand("CommercePlatform", Value.from_any(getattr(self, "id", None)), getattr(self, "version", None))
            for key, value in payload.items():
                if key not in ("id", "version"): cmd.value(key, value)
        else:
            cmd = DeleteCommand("CommercePlatform", Value.from_any(getattr(self, "id", None)), getattr(self, "version", None))
        return action, cmd

    def _teaql_preflight_graph(self, context):
        if not self._comment or not self._comment.strip():
            raise Exception("Security audit failure: audit_as() must be called before save()")
        if self._action == "Update":
            if "id" not in self._loaded_fields:
                raise CheckException([CheckResult("invalid_type", ObjectLocation().property("id"), message="Mutation requires a fully loaded entity")])
            if "name" not in self._loaded_fields:
                raise CheckException([CheckResult("invalid_type", ObjectLocation().property("name"), message="Mutation requires a fully loaded entity")])
            if "createTime" not in self._loaded_fields:
                raise CheckException([CheckResult("invalid_type", ObjectLocation().property("create_time"), message="Mutation requires a fully loaded entity")])
            if "updateTime" not in self._loaded_fields:
                raise CheckException([CheckResult("invalid_type", ObjectLocation().property("update_time"), message="Mutation requires a fully loaded entity")])
            if "version" not in self._loaded_fields:
                raise CheckException([CheckResult("invalid_type", ObjectLocation().property("version"), message="Mutation requires a fully loaded entity")])
        _action, cmd = self._teaql_build_command()
        try:
            context.check_and_fix_mutation(cmd)
        finally:
            for field, value in getattr(cmd, "values", {}).items():
                if field not in ("id", "version"):
                    self._entity_root.set(self._teaql_entity_key(), field, value)
        for index, child in enumerate(self._customer_list):
            child._teaql_attach_root(self._entity_root)
            setattr(child, "commercePlatform", self)
            child._loaded_fields.add("commercePlatform")
            child._entity_root.set(child._teaql_entity_key(), "commerce_platform", Value.Object(self))
            child.audit_as(self._comment)
            try:
                child._teaql_preflight_graph(context)
            except CheckException as error:
                prefix = ObjectLocation().property("customer_list").index(index)
                raise CheckException([
                    CheckResult(v.rule_id, v.location.prefixed_by(prefix), v.input_value, v.system_value, v.message)
                    for v in error.violations
                ]) from error
        for index, child in enumerate(self._order_status_list):
            child._teaql_attach_root(self._entity_root)
            setattr(child, "commercePlatform", self)
            child._loaded_fields.add("commercePlatform")
            child._entity_root.set(child._teaql_entity_key(), "commerce_platform", Value.Object(self))
            child.audit_as(self._comment)
            try:
                child._teaql_preflight_graph(context)
            except CheckException as error:
                prefix = ObjectLocation().property("order_status_list").index(index)
                raise CheckException([
                    CheckResult(v.rule_id, v.location.prefixed_by(prefix), v.input_value, v.system_value, v.message)
                    for v in error.violations
                ]) from error
        for index, child in enumerate(self._customer_order_list):
            child._teaql_attach_root(self._entity_root)
            setattr(child, "commercePlatform", self)
            child._loaded_fields.add("commercePlatform")
            child._entity_root.set(child._teaql_entity_key(), "commerce_platform", Value.Object(self))
            child.audit_as(self._comment)
            try:
                child._teaql_preflight_graph(context)
            except CheckException as error:
                prefix = ObjectLocation().property("customer_order_list").index(index)
                raise CheckException([
                    CheckResult(v.rule_id, v.location.prefixed_by(prefix), v.input_value, v.system_value, v.message)
                    for v in error.violations
                ]) from error
        for index, child in enumerate(self._product_list):
            child._teaql_attach_root(self._entity_root)
            setattr(child, "commercePlatform", self)
            child._loaded_fields.add("commercePlatform")
            child._entity_root.set(child._teaql_entity_key(), "commerce_platform", Value.Object(self))
            child.audit_as(self._comment)
            try:
                child._teaql_preflight_graph(context)
            except CheckException as error:
                prefix = ObjectLocation().property("product_list").index(index)
                raise CheckException([
                    CheckResult(v.rule_id, v.location.prefixed_by(prefix), v.input_value, v.system_value, v.message)
                    for v in error.violations
                ]) from error
        for index, child in enumerate(self._order_line_list):
            child._teaql_attach_root(self._entity_root)
            setattr(child, "commercePlatform", self)
            child._loaded_fields.add("commercePlatform")
            child._entity_root.set(child._teaql_entity_key(), "commerce_platform", Value.Object(self))
            child.audit_as(self._comment)
            try:
                child._teaql_preflight_graph(context)
            except CheckException as error:
                prefix = ObjectLocation().property("order_line_list").index(index)
                raise CheckException([
                    CheckResult(v.rule_id, v.location.prefixed_by(prefix), v.input_value, v.system_value, v.message)
                    for v in error.violations
                ]) from error
        for index, child in enumerate(self._order_search_preset_list):
            child._teaql_attach_root(self._entity_root)
            setattr(child, "commercePlatform", self)
            child._loaded_fields.add("commercePlatform")
            child._entity_root.set(child._teaql_entity_key(), "commerce_platform", Value.Object(self))
            child.audit_as(self._comment)
            try:
                child._teaql_preflight_graph(context)
            except CheckException as error:
                prefix = ObjectLocation().property("order_search_preset_list").index(index)
                raise CheckException([
                    CheckResult(v.rule_id, v.location.prefixed_by(prefix), v.input_value, v.system_value, v.message)
                    for v in error.violations
                ]) from error

    async def _teaql_save_within_graph(self, context):
        if not self._comment or not self._comment.strip():
            raise Exception("Security audit failure: audit_as() must be called before save()")

        self._teaql_attach_root(self._entity_root)
        action, cmd = self._teaql_build_command()


        req = MutationRequest(cmd)
        if self._comment:
            req.comment = self._comment

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
                "Mutation provider did not return authoritative persisted state for CommercePlatform"
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
        if "name" in persisted:
            self.name = persisted["name"]
            self._loaded_fields.add("name")
        elif "name" in persisted:
            self.name = persisted["name"]
            self._loaded_fields.add("name")
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
            if old_key != new_key:
                self._entity_root.rekey(new_key, old_key)
        context.after_graph_rollback(rollback_entity)
        if action != "Delete":
            self._action = "Update"

        cascade_relations = []
        cascade_relations.append(("customer_list", self._customer_list, "update_commerce_platform"))
        cascade_relations.append(("order_status_list", self._order_status_list, "update_commerce_platform"))
        cascade_relations.append(("customer_order_list", self._customer_order_list, "update_commerce_platform"))
        cascade_relations.append(("product_list", self._product_list, "update_commerce_platform"))
        cascade_relations.append(("order_line_list", self._order_line_list, "update_commerce_platform"))
        cascade_relations.append(("order_search_preset_list", self._order_search_preset_list, "update_commerce_platform"))
        if action != "Delete":
            for relation_name, children, updater in cascade_relations:
                for index, child in enumerate(children):
                    child._teaql_attach_root(self._entity_root)
                    getattr(child, updater)(self)
                    child.audit_as(self._comment)
                    try:
                        await child._teaql_save_within_graph(context)
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
        def commit_entity():
            self._entity_root.clear_entity(new_key)
            if getattr(self, "version", None) is not None:
                self._entity_root.set_original_version(new_key, int(self.version))
        context.after_graph_commit(commit_entity)
        return self

    def update_id(self, value):
        self.id = value
        self._loaded_fields.add("id")
        self._entity_root.set(self._teaql_entity_key(), "id", Value.from_any(value))
        return self

    def update_name(self, value):
        self.name = value
        self._loaded_fields.add("name")
        self._entity_root.set(self._teaql_entity_key(), "name", Value.from_any(value))
        return self

    def update_create_time(self, value):
        self.createTime = value
        self._loaded_fields.add("createTime")
        self._entity_root.set(self._teaql_entity_key(), "create_time", Value.from_any(value))
        return self

    def update_update_time(self, value):
        self.updateTime = value
        self._loaded_fields.add("updateTime")
        self._entity_root.set(self._teaql_entity_key(), "update_time", Value.from_any(value))
        return self

    def update_version(self, value):
        self.version = value
        self._loaded_fields.add("version")
        self._entity_root.set(self._teaql_entity_key(), "version", Value.from_any(value))
        return self
    def customer_list(self) -> list:
        self._loaded_fields.add("customer_list")
        return self._customer_list

    def order_status_list(self) -> list:
        self._loaded_fields.add("order_status_list")
        return self._order_status_list

    def customer_order_list(self) -> list:
        self._loaded_fields.add("customer_order_list")
        return self._customer_order_list

    def product_list(self) -> list:
        self._loaded_fields.add("product_list")
        return self._product_list

    def order_line_list(self) -> list:
        self._loaded_fields.add("order_line_list")
        return self._order_line_list

    def order_search_preset_list(self) -> list:
        self._loaded_fields.add("order_search_preset_list")
        return self._order_search_preset_list