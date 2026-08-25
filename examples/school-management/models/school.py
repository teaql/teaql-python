from teaql.core.mutation import InsertCommand, UpdateCommand, DeleteCommand, MutationRequest
from teaql.core.value import Value
from teaql.runtime import EntityKey, EntityRoot
import itertools
from models.platform import Platform
from models.school_type import SchoolType

class School:
    _teaql_temporary_ids = itertools.count(1)
    @classmethod
    def refer(cls, entity_id):
        return cls(id=entity_id)

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
    def mark_as_deleted(self):
        self._action = "Delete"
        self._entity_root.mark_as_deleted(self._teaql_entity_key())
        return self

    def audit_as(self, comment: str):
        if not isinstance(comment, str) or not comment.strip():
            raise ValueError("Security audit failure: audit_as() requires a non-empty reason")
        self._comment = comment
        return self

    async def save(self, context):
        if not self._comment or not self._comment.strip():
            raise Exception("Security audit failure: audit_as() must be called before save()")

        self._teaql_attach_root(self._entity_root)
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
            payload["student_capacity"] = Value.Object(self.studentCapacity)
        if "active" in self._loaded_fields:
            payload["active"] = Value.Object(self.active)
        if "createTime" in self._loaded_fields:
            payload["create_time"] = Value.Date(self.createTime)
        if "updateTime" in self._loaded_fields:
            payload["update_time"] = Value.Date(self.updateTime)
        if "version" in self._loaded_fields:
            payload["version"] = Value.I64(self.version)

        action = self._action
        if action == "Update":
            ledger = dict(self._entity_root.current_change_set().changes()).get(self._teaql_entity_key(), {})
            payload = {field: value for field, value in ledger.items() if field not in ("id", "version")}
        if action == "Create":
            cmd = InsertCommand("School", payload)
        elif self._action == "Update":
            cmd = UpdateCommand(
                "School",
                Value.from_any(getattr(self, "id", None)),
                getattr(self, "version", None),
            )
            for k, v in payload.items():
                if k not in ("id", "version"):
                    cmd.value(k, v)
        elif self._action == "Delete":
            cmd = DeleteCommand(
                "School",
                Value.from_any(getattr(self, "id", None)),
                getattr(self, "version", None),
            )


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
        old_key = self._teaql_entity_key()
        for field, value in persisted.items():
            setattr(self, field, value)
        self._ledger_id = getattr(self, "id", self._ledger_id)
        new_key = self._teaql_entity_key()
        if old_key != new_key:
            self._entity_root.rekey(old_key, new_key)
        self._loaded_fields.update(persisted.keys())
        if action != "Delete":
            self._action = "Update"

        cascade_relations = []
        if action != "Delete":
            for children, updater in cascade_relations:
                for child in children:
                    getattr(child, updater)(self)
                    child.audit_as(self._comment)
                    await child.save(context)
        self._entity_root.clear_entity(new_key)
        if getattr(self, "version", None) is not None:
            self._entity_root.set_original_version(new_key, int(self.version))
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

