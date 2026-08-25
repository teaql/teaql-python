from teaql.core.mutation import InsertCommand, UpdateCommand, DeleteCommand, MutationRequest
from teaql.core.value import Value
from teaql.runtime import EntityKey, EntityRoot
import itertools
from models.platform import Platform

class WorkItem:
    _teaql_temporary_ids = itertools.count(1)
    @classmethod
    def refer(cls, entity_id):
        return cls(id=entity_id)

    def __init__(self, **kwargs):
        self._entity_root = kwargs.pop("_entity_root", None) or EntityRoot()
        self._action = "Update" if kwargs.get("id") else "Create"
        self._comment = None
        self._loaded_fields = set(kwargs.keys())
        self.id = kwargs.get("id")
        self.title = kwargs.get("title")
        self.description = kwargs.get("description")
        self.platform = kwargs.get("platform")
        self.version = kwargs.get("version")
        if isinstance(self.platform, dict):
            self.platform = Platform(**self.platform)
        self._ledger_id = getattr(self, "id", None)
        if self._ledger_id is None:
            self._ledger_id = -next(self._teaql_temporary_ids)
        key = self._teaql_entity_key()
        if self._action == "Create":
            self._entity_root.mark_as_new(key)
        elif getattr(self, "version", None) is not None:
            self._entity_root.set_original_version(key, int(self.version))

    def _teaql_entity_key(self):
        return EntityKey("WorkItem", self._ledger_id)

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
        if "title" in self._loaded_fields:
            payload["title"] = Value.Text(self.title)
        if "description" in self._loaded_fields:
            payload["description"] = Value.Text(self.description)
        if "platform" in self._loaded_fields:
            payload["platform"] = Value.Object(self.platform)
        if "version" in self._loaded_fields:
            payload["version"] = Value.I64(self.version)

        action = self._action
        if action == "Update":
            ledger = dict(self._entity_root.current_change_set().changes()).get(self._teaql_entity_key(), {})
            payload = {field: value for field, value in ledger.items() if field not in ("id", "version")}
        if action == "Create":
            cmd = InsertCommand("WorkItem", payload)
        elif self._action == "Update":
            cmd = UpdateCommand(
                "WorkItem",
                Value.from_any(getattr(self, "id", None)),
                getattr(self, "version", None),
            )
            for k, v in payload.items():
                if k not in ("id", "version"):
                    cmd.value(k, v)
        elif self._action == "Delete":
            cmd = DeleteCommand(
                "WorkItem",
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
                "Mutation provider did not return authoritative persisted state for WorkItem"
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

    def update_title(self, value):
        self.title = value
        self._loaded_fields.add("title")
        self._entity_root.set(self._teaql_entity_key(), "title", Value.from_any(value))
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

