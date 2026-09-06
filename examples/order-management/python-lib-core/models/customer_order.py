from teaql.core.mutation import InsertCommand, UpdateCommand, DeleteCommand, MutationRequest
from teaql.core.value import Value
from teaql.runtime import CheckException, CheckResult, EntityKey, EntityRoot, ObjectLocation
import itertools
from models.order_status import OrderStatus
from models.customer import Customer
from models.commerce_platform import CommercePlatform

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
        if "order_number" in kwargs and "orderNumber" not in kwargs:
            kwargs["orderNumber"] = kwargs.pop("order_number")
        if "order_date" in kwargs and "orderDate" not in kwargs:
            kwargs["orderDate"] = kwargs.pop("order_date")
        if "total_amount" in kwargs and "totalAmount" not in kwargs:
            kwargs["totalAmount"] = kwargs.pop("total_amount")
        if "status" in kwargs and "status" not in kwargs:
            kwargs["status"] = kwargs.pop("status")
        if "customer" in kwargs and "customer" not in kwargs:
            kwargs["customer"] = kwargs.pop("customer")
        if "commerce_platform" in kwargs and "commercePlatform" not in kwargs:
            kwargs["commercePlatform"] = kwargs.pop("commerce_platform")
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
        self.orderNumber = kwargs.get("orderNumber")
        self.orderDate = kwargs.get("orderDate")
        self.totalAmount = kwargs.get("totalAmount")
        self.status = kwargs.get("status")
        self.customer = kwargs.get("customer")
        self.commercePlatform = kwargs.get("commercePlatform")
        self.createTime = kwargs.get("createTime")
        self.updateTime = kwargs.get("updateTime")
        self.version = kwargs.get("version")
        if isinstance(self.status, dict):
            self.status = OrderStatus(**self.status)
        if isinstance(self.customer, dict):
            self.customer = Customer(**self.customer)
        if isinstance(self.commercePlatform, dict):
            self.commercePlatform = CommercePlatform(**self.commercePlatform)
        self._order_line_list = kwargs.get("order_line_list", [])
        if "order_line_list" in kwargs or kwargs.get("id") is None:
            self._loaded_fields.add("order_line_list")
        if self._order_line_list:
            from models.order_line import OrderLine
            self._order_line_list = [
                item if isinstance(item, OrderLine) else OrderLine(**item)
                for item in self._order_line_list
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
        if self._entity_root is not root:
            root.merge_from(self._entity_root)
            self._entity_root = root
        for child in self._order_line_list:
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
        if "orderNumber" in self._loaded_fields:
            payload["order_number"] = Value.Text(self.orderNumber)
        if "orderDate" in self._loaded_fields:
            payload["order_date"] = Value.Date(self.orderDate)
        if "totalAmount" in self._loaded_fields:
            payload["total_amount"] = Value.Decimal(self.totalAmount)
        if "status" in self._loaded_fields:
            payload["status"] = Value.Object(self.status)
        if "customer" in self._loaded_fields:
            payload["customer"] = Value.Object(self.customer)
        if "commercePlatform" in self._loaded_fields:
            payload["commerce_platform"] = Value.Object(self.commercePlatform)
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
            cmd = InsertCommand("CustomerOrder", payload)
        elif action == "Update":
            cmd = UpdateCommand("CustomerOrder", Value.from_any(getattr(self, "id", None)), getattr(self, "version", None))
            for key, value in payload.items():
                if key not in ("id", "version"): cmd.value(key, value)
        else:
            cmd = DeleteCommand("CustomerOrder", Value.from_any(getattr(self, "id", None)), getattr(self, "version", None))
        return action, cmd

    def _teaql_preflight_graph(self, context):
        if not self._comment or not self._comment.strip():
            raise Exception("Security audit failure: audit_as() must be called before save()")
        if self._action == "Update":
            if "id" not in self._loaded_fields:
                raise CheckException([CheckResult("invalid_type", ObjectLocation().property("id"), message="Mutation requires a fully loaded entity")])
            if "orderNumber" not in self._loaded_fields:
                raise CheckException([CheckResult("invalid_type", ObjectLocation().property("order_number"), message="Mutation requires a fully loaded entity")])
            if "orderDate" not in self._loaded_fields:
                raise CheckException([CheckResult("invalid_type", ObjectLocation().property("order_date"), message="Mutation requires a fully loaded entity")])
            if "totalAmount" not in self._loaded_fields:
                raise CheckException([CheckResult("invalid_type", ObjectLocation().property("total_amount"), message="Mutation requires a fully loaded entity")])
            if "status" not in self._loaded_fields:
                raise CheckException([CheckResult("invalid_type", ObjectLocation().property("status"), message="Mutation requires a fully loaded entity")])
            if "customer" not in self._loaded_fields:
                raise CheckException([CheckResult("invalid_type", ObjectLocation().property("customer"), message="Mutation requires a fully loaded entity")])
            if "commercePlatform" not in self._loaded_fields:
                raise CheckException([CheckResult("invalid_type", ObjectLocation().property("commerce_platform"), message="Mutation requires a fully loaded entity")])
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
        for index, child in enumerate(self._order_line_list):
            child._teaql_attach_root(self._entity_root)
            setattr(child, "customerOrder", self)
            child._loaded_fields.add("customerOrder")
            child._entity_root.set(child._teaql_entity_key(), "customer_order", Value.Object(self))
            child.audit_as(self._comment)
            try:
                child._teaql_preflight_graph(context)
            except CheckException as error:
                prefix = ObjectLocation().property("order_line_list").index(index)
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
        if "order_number" in persisted:
            self.orderNumber = persisted["order_number"]
            self._loaded_fields.add("orderNumber")
        elif "orderNumber" in persisted:
            self.orderNumber = persisted["orderNumber"]
            self._loaded_fields.add("orderNumber")
        if "order_date" in persisted:
            self.orderDate = persisted["order_date"]
            self._loaded_fields.add("orderDate")
        elif "orderDate" in persisted:
            self.orderDate = persisted["orderDate"]
            self._loaded_fields.add("orderDate")
        if "total_amount" in persisted:
            self.totalAmount = persisted["total_amount"]
            self._loaded_fields.add("totalAmount")
        elif "totalAmount" in persisted:
            self.totalAmount = persisted["totalAmount"]
            self._loaded_fields.add("totalAmount")
        if "status" in persisted:
            self.status = persisted["status"]
            self._loaded_fields.add("status")
        elif "status" in persisted:
            self.status = persisted["status"]
            self._loaded_fields.add("status")
        if "customer" in persisted:
            self.customer = persisted["customer"]
            self._loaded_fields.add("customer")
        elif "customer" in persisted:
            self.customer = persisted["customer"]
            self._loaded_fields.add("customer")
        if "commerce_platform" in persisted:
            self.commercePlatform = persisted["commerce_platform"]
            self._loaded_fields.add("commercePlatform")
        elif "commercePlatform" in persisted:
            self.commercePlatform = persisted["commercePlatform"]
            self._loaded_fields.add("commercePlatform")
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
        cascade_relations.append(("order_line_list", self._order_line_list, "update_customer_order"))
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

    def update_order_number(self, value):
        self.orderNumber = value
        self._loaded_fields.add("orderNumber")
        self._entity_root.set(self._teaql_entity_key(), "order_number", Value.from_any(value))
        return self

    def update_order_date(self, value):
        self.orderDate = value
        self._loaded_fields.add("orderDate")
        self._entity_root.set(self._teaql_entity_key(), "order_date", Value.from_any(value))
        return self

    def update_total_amount(self, value):
        self.totalAmount = value
        self._loaded_fields.add("totalAmount")
        self._entity_root.set(self._teaql_entity_key(), "total_amount", Value.from_any(value))
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
    def update_status(self, value):
        self.status = getattr(value, "id", value) if value else None
        self._loaded_fields.add("status")
        self._entity_root.set(self._teaql_entity_key(), "status", Value.from_any(self.status))
        return self
    def update_status_to_pending(self):
        self.status = 1001
        self._loaded_fields.add("status")
        return self
    def update_status_to_confirmed(self):
        self.status = 1002
        self._loaded_fields.add("status")
        return self


    def update_customer(self, value):
        self.customer = getattr(value, "id", value) if value else None
        self._loaded_fields.add("customer")
        self._entity_root.set(self._teaql_entity_key(), "customer", Value.from_any(self.customer))
        return self


    def update_commerce_platform(self, value):
        self.commercePlatform = getattr(value, "id", value) if value else None
        self._loaded_fields.add("commercePlatform")
        self._entity_root.set(self._teaql_entity_key(), "commerce_platform", Value.from_any(self.commercePlatform))
        return self

    def order_line_list(self) -> list:
        self._loaded_fields.add("order_line_list")
        return self._order_line_list