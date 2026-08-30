from teaql.core.mutation import InsertCommand, UpdateCommand, DeleteCommand, MutationRequest
from teaql.core.value import Value
from teaql.runtime import EntityKey, EntityRoot
import itertools
from models.platform import Platform

class SchoolType:
    _teaql_temporary_ids = itertools.count(1)
    @classmethod
    def refer(cls, entity_id):
        return cls(id=entity_id)

    def __init__(self, **kwargs):
        self._entity_root = kwargs.pop("_entity_root", None) or EntityRoot()
        if "platform" in kwargs and "platform" not in kwargs:
            kwargs["platform"] = kwargs.pop("platform")
        if "id" in kwargs and "id" not in kwargs:
            kwargs["id"] = kwargs.pop("id")
        if "name" in kwargs and "name" not in kwargs:
            kwargs["name"] = kwargs.pop("name")
        if "code" in kwargs and "code" not in kwargs:
            kwargs["code"] = kwargs.pop("code")
        if "display_order" in kwargs and "displayOrder" not in kwargs:
            kwargs["displayOrder"] = kwargs.pop("display_order")
        if "version" in kwargs and "version" not in kwargs:
            kwargs["version"] = kwargs.pop("version")
        self._action = "Update" if kwargs.get("id") else "Create"
        self._comment = None
        self._loaded_fields = set(kwargs.keys())
        self.platform = kwargs.get("platform")
        self.id = kwargs.get("id")
        self.name = kwargs.get("name")
        self.code = kwargs.get("code")
        self.displayOrder = kwargs.get("displayOrder")
        self.version = kwargs.get("version")
        if isinstance(self.platform, dict):
            self.platform = Platform(**self.platform)
        self._school_list = kwargs.get("school_list", [])
        if "school_list" in kwargs or kwargs.get("id") is None:
            self._loaded_fields.add("school_list")
        self._ledger_id = getattr(self, "id", None)
        if self._ledger_id is None:
            self._ledger_id = -next(self._teaql_temporary_ids)
        key = self._teaql_entity_key()
        if self._action == "Create":
            self._entity_root.mark_as_new(key)
        elif getattr(self, "version", None) is not None:
            self._entity_root.set_original_version(key, int(self.version))

    def _teaql_entity_key(self):
        return EntityKey("SchoolType", self._ledger_id)

    def _teaql_attach_root(self, root):
        if self._entity_root is not root:
            root.merge_from(self._entity_root)
            self._entity_root = root
        for child in self._school_list:
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
        if not self._comment or not self._comment.strip():
            raise Exception("Security audit failure: audit_as() must be called before save()")

        self._teaql_attach_root(self._entity_root)
        payload = {}
        if "platform" in self._loaded_fields:
            payload["platform"] = Value.Object(self.platform)
        if "id" in self._loaded_fields:
            payload["id"] = Value.I64(self.id)
        if "name" in self._loaded_fields:
            payload["name"] = Value.Text(self.name)
        if "code" in self._loaded_fields:
            payload["code"] = Value.Text(self.code)
        if "displayOrder" in self._loaded_fields:
            payload["display_order"] = Value.Decimal(self.displayOrder)
        if "version" in self._loaded_fields:
            payload["version"] = Value.I64(self.version)

        action = self._action
        if action == "Update":
            ledger = dict(self._entity_root.current_change_set().changes()).get(self._teaql_entity_key(), {})
            payload = {field: value for field, value in ledger.items() if field not in ("id", "version")}
        if action == "Create":
            cmd = InsertCommand("SchoolType", payload)
        elif self._action == "Update":
            cmd = UpdateCommand(
                "SchoolType",
                Value.from_any(getattr(self, "id", None)),
                getattr(self, "version", None),
            )
            for k, v in payload.items():
                if k not in ("id", "version"):
                    cmd.value(k, v)
        elif self._action == "Delete":
            cmd = DeleteCommand(
                "SchoolType",
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
                "Mutation provider did not return authoritative persisted state for SchoolType"
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
        cascade_relations.append((self._school_list, "update_school_type"))
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

    def update_code(self, value):
        self.code = value
        self._loaded_fields.add("code")
        self._entity_root.set(self._teaql_entity_key(), "code", Value.from_any(value))
        return self

    def update_display_order(self, value):
        self.displayOrder = value
        self._loaded_fields.add("displayOrder")
        self._entity_root.set(self._teaql_entity_key(), "display_order", Value.from_any(value))
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

    def school_list(self) -> list:
        self._loaded_fields.add("school_list")
        return self._school_list