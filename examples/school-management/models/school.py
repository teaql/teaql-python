from teaql.core.mutation import InsertCommand, UpdateCommand, DeleteCommand, MutationRequest
from teaql.core.value import Value
from teaql.runtime import CheckException, CheckResult, EntityKey, EntityRoot, ObjectLocation
import itertools
from models.platform import Platform
from models.school_type import SchoolType

class School:
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
        if "school_type" in kwargs and "schoolType" not in kwargs:
            kwargs["schoolType"] = kwargs.pop("school_type")
        if "name" in kwargs and "name" not in kwargs:
            kwargs["name"] = kwargs.pop("name")
        if "address" in kwargs and "address" not in kwargs:
            kwargs["address"] = kwargs.pop("address")
        if "established_date" in kwargs and "establishedDate" not in kwargs:
            kwargs["establishedDate"] = kwargs.pop("established_date")
        if "student_capacity" in kwargs and "studentCapacity" not in kwargs:
            kwargs["studentCapacity"] = kwargs.pop("student_capacity")
        if "active" in kwargs and "active" not in kwargs:
            kwargs["active"] = kwargs.pop("active")
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
        self.platform = kwargs.get("platform")
        self.schoolType = kwargs.get("schoolType")
        self.name = kwargs.get("name")
        self.address = kwargs.get("address")
        self.establishedDate = kwargs.get("establishedDate")
        self.studentCapacity = kwargs.get("studentCapacity")
        self.active = kwargs.get("active")
        self.createTime = kwargs.get("createTime")
        self.updateTime = kwargs.get("updateTime")
        self.version = kwargs.get("version")
        if isinstance(self.platform, dict):
            self.platform = Platform(**self.platform)
        if isinstance(self.schoolType, dict):
            self.schoolType = SchoolType(**self.schoolType)
        self._ledger_id = getattr(self, "id", None)
        if self._ledger_id is None:
            self._ledger_id = -next(self._teaql_temporary_ids)
        key = self._teaql_entity_key()
        if self._action == "Create":
            self._entity_root.mark_as_new(key)
        elif getattr(self, "version", None) is not None:
            self._entity_root.set_original_version(key, int(self.version))

    def _teaql_entity_key(self):
        return EntityKey("School", self._ledger_id)

    def _teaql_attach_root(self, root):
        if self._entity_root is not root:
            root.merge_from(self._entity_root)
            self._entity_root = root
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
        if "platform" in self._loaded_fields:
            payload["platform"] = Value.Object(self.platform)
        if "schoolType" in self._loaded_fields:
            payload["school_type"] = Value.Object(self.schoolType)
        if "name" in self._loaded_fields:
            payload["name"] = Value.Text(self.name)
        if "address" in self._loaded_fields:
            payload["address"] = Value.Text(self.address)
        if "establishedDate" in self._loaded_fields:
            payload["established_date"] = Value.Date(self.establishedDate)
        if "studentCapacity" in self._loaded_fields:
            payload["student_capacity"] = Value.I64(self.studentCapacity)
        if "active" in self._loaded_fields:
            payload["active"] = Value.Bool(self.active)
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
            cmd = InsertCommand("School", payload)
        elif action == "Update":
            cmd = UpdateCommand("School", Value.from_any(getattr(self, "id", None)), getattr(self, "version", None))
            for key, value in payload.items():
                if key not in ("id", "version"): cmd.value(key, value)
        else:
            cmd = DeleteCommand("School", Value.from_any(getattr(self, "id", None)), getattr(self, "version", None))
        return action, cmd

    def _teaql_preflight_graph(self, context):
        if not self._comment or not self._comment.strip():
            raise Exception("Security audit failure: audit_as() must be called before save()")
        if self._action == "Update":
            if "id" not in self._loaded_fields:
                raise CheckException([CheckResult("invalid_type", ObjectLocation().property("id"), message="Mutation requires a fully loaded entity")])
            if "platform" not in self._loaded_fields:
                raise CheckException([CheckResult("invalid_type", ObjectLocation().property("platform"), message="Mutation requires a fully loaded entity")])
            if "schoolType" not in self._loaded_fields:
                raise CheckException([CheckResult("invalid_type", ObjectLocation().property("school_type"), message="Mutation requires a fully loaded entity")])
            if "name" not in self._loaded_fields:
                raise CheckException([CheckResult("invalid_type", ObjectLocation().property("name"), message="Mutation requires a fully loaded entity")])
            if "address" not in self._loaded_fields:
                raise CheckException([CheckResult("invalid_type", ObjectLocation().property("address"), message="Mutation requires a fully loaded entity")])
            if "establishedDate" not in self._loaded_fields:
                raise CheckException([CheckResult("invalid_type", ObjectLocation().property("established_date"), message="Mutation requires a fully loaded entity")])
            if "studentCapacity" not in self._loaded_fields:
                raise CheckException([CheckResult("invalid_type", ObjectLocation().property("student_capacity"), message="Mutation requires a fully loaded entity")])
            if "active" not in self._loaded_fields:
                raise CheckException([CheckResult("invalid_type", ObjectLocation().property("active"), message="Mutation requires a fully loaded entity")])
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
                "Mutation provider did not return authoritative persisted state for School"
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
        if "school_type" in persisted:
            self.schoolType = persisted["school_type"]
            self._loaded_fields.add("schoolType")
        elif "schoolType" in persisted:
            self.schoolType = persisted["schoolType"]
            self._loaded_fields.add("schoolType")
        if "name" in persisted:
            self.name = persisted["name"]
            self._loaded_fields.add("name")
        elif "name" in persisted:
            self.name = persisted["name"]
            self._loaded_fields.add("name")
        if "address" in persisted:
            self.address = persisted["address"]
            self._loaded_fields.add("address")
        elif "address" in persisted:
            self.address = persisted["address"]
            self._loaded_fields.add("address")
        if "established_date" in persisted:
            self.establishedDate = persisted["established_date"]
            self._loaded_fields.add("establishedDate")
        elif "establishedDate" in persisted:
            self.establishedDate = persisted["establishedDate"]
            self._loaded_fields.add("establishedDate")
        if "student_capacity" in persisted:
            self.studentCapacity = persisted["student_capacity"]
            self._loaded_fields.add("studentCapacity")
        elif "studentCapacity" in persisted:
            self.studentCapacity = persisted["studentCapacity"]
            self._loaded_fields.add("studentCapacity")
        if "active" in persisted:
            self.active = persisted["active"]
            self._loaded_fields.add("active")
        elif "active" in persisted:
            self.active = persisted["active"]
            self._loaded_fields.add("active")
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

    def update_address(self, value):
        self.address = value
        self._loaded_fields.add("address")
        self._entity_root.set(self._teaql_entity_key(), "address", Value.from_any(value))
        return self

    def update_established_date(self, value):
        self.establishedDate = value
        self._loaded_fields.add("establishedDate")
        self._entity_root.set(self._teaql_entity_key(), "established_date", Value.from_any(value))
        return self

    def update_student_capacity(self, value):
        self.studentCapacity = value
        self._loaded_fields.add("studentCapacity")
        self._entity_root.set(self._teaql_entity_key(), "student_capacity", Value.from_any(value))
        return self

    def update_active(self, value):
        self.active = value
        self._loaded_fields.add("active")
        self._entity_root.set(self._teaql_entity_key(), "active", Value.from_any(value))
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
    def update_platform(self, value):
        self.platform = getattr(value, "id", value) if value else None
        self._loaded_fields.add("platform")
        self._entity_root.set(self._teaql_entity_key(), "platform", Value.from_any(self.platform))
        return self


    def update_school_type(self, value):
        self.schoolType = getattr(value, "id", value) if value else None
        self._loaded_fields.add("schoolType")
        self._entity_root.set(self._teaql_entity_key(), "school_type", Value.from_any(self.schoolType))
        return self
    def update_school_type_to_primary(self):
        self.schoolType = 1001
        self._loaded_fields.add("schoolType")
        return self

