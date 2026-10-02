from teaql.core.mutation import InsertCommand, UpdateCommand, DeleteCommand, MutationRequest
from teaql.core import MutationIntent
from teaql.core.value import Value
from teaql.runtime import CheckException, CheckResult, EntityKey, EntityRoot, ObjectLocation
import itertools
from models.task import Task


class TaskExecutionLog:
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
        if "task" in kwargs and "task" not in kwargs:
            kwargs["task"] = kwargs.pop("task")
        if "action" in kwargs and "action" not in kwargs:
            kwargs["action"] = kwargs.pop("action")
        if "detail" in kwargs and "detail" not in kwargs:
            kwargs["detail"] = kwargs.pop("detail")
        if "version" in kwargs and "version" not in kwargs:
            kwargs["version"] = kwargs.pop("version")
        self._action = "Update" if kwargs.get("id") else "Create"
        self._comment = None
        self._loaded_fields = set(kwargs.keys())
        self.id = kwargs.get("id")

        self.task = kwargs.get("task")

        self.action = kwargs.get("action")

        self.detail = kwargs.get("detail")

        self.version = kwargs.get("version")

        if isinstance(self.task, dict):
            self.task = Task(**self.task)
        self._ledger_id = getattr(self, "id", None)
        if self._ledger_id is None:
            self._ledger_id = -next(self._teaql_temporary_ids)
        key = self._teaql_entity_key()
        if self._action == "Create":
            self._entity_root.mark_as_new(key)
        elif getattr(self, "version", None) is not None:
            self._entity_root.set_original_version(key, int(self.version))

    def _teaql_entity_key(self):
        return EntityKey("TaskExecutionLog", self._ledger_id)

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
            self.id = int(await allocator("TaskExecutionLog"))
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

    async def _teaql_preflight_and_save(self, graph):
        await self._teaql_reserve_graph_ids(graph, set())
        self._teaql_preflight_graph(graph)
        return await self._teaql_save_within_graph(graph)

    def _teaql_build_command(self):
        payload = {}
        if "id" in self._loaded_fields:
            payload["id"] = Value.I64(self.id)

        if "task" in self._loaded_fields:
            reference = self.task
            reference_id = getattr(reference, "id", reference)
            payload["task"] = (Value.Object(reference)
                if reference is not None and hasattr(reference, "id") and reference_id is None
                else Value.I64(reference_id))

        if "action" in self._loaded_fields:
            payload["action"] = Value.Text(self.action)

        if "detail" in self._loaded_fields:
            payload["detail"] = Value.Text(self.detail)

        if "version" in self._loaded_fields:
            payload["version"] = Value.I64(self.version)

        action = self._action
        if action == "Update":
            ledger = dict(self._entity_root.current_change_set().changes()).get(self._teaql_entity_key(), {})
            payload = {field: value for field, value in ledger.items() if field not in ("id", "version")}
        if action == "Create":
            cmd = InsertCommand("TaskExecutionLog", payload)
        elif action == "Update":
            cmd = UpdateCommand("TaskExecutionLog", Value.from_any(getattr(self, "id", None)), getattr(self, "version", None))
            for key, value in payload.items():
                if key not in ("id", "version"): cmd.value(key, value)
        else:
            cmd = DeleteCommand("TaskExecutionLog", Value.from_any(getattr(self, "id", None)), getattr(self, "version", None))
        return action, cmd

    def _teaql_preflight_graph(self, graph):
        context = graph.context
        if self._action == "Update":
            if "id" not in self._loaded_fields:
                raise CheckException([CheckResult("invalid_type", ObjectLocation().property("id"), message="Mutation requires a fully loaded entity")])
            if "task" not in self._loaded_fields:
                raise CheckException([CheckResult("invalid_type", ObjectLocation().property("task"), message="Mutation requires a fully loaded entity")])
            if "action" not in self._loaded_fields:
                raise CheckException([CheckResult("invalid_type", ObjectLocation().property("action"), message="Mutation requires a fully loaded entity")])
            if "detail" not in self._loaded_fields:
                raise CheckException([CheckResult("invalid_type", ObjectLocation().property("detail"), message="Mutation requires a fully loaded entity")])
            if "version" not in self._loaded_fields:
                raise CheckException([CheckResult("invalid_type", ObjectLocation().property("version"), message="Mutation requires a fully loaded entity")])
        _action, cmd = self._teaql_build_command()
        try:
            context.preflight_mutation(cmd)
        finally:
            for field, value in getattr(cmd, "values", {}).items():
                if field not in ("id", "version"):
                    self._entity_root.set(self._teaql_entity_key(), field, value)

    async def _teaql_save_within_graph(self, graph, parent_scope=None):
        context = graph.context
        scope = graph.scope(self._teaql_entity_key(), parent_scope, self._comment)

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
                "Mutation provider did not return authoritative persisted state for TaskExecutionLog"
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
        if "task" in persisted:
            self.task = persisted["task"]
            self._loaded_fields.add("task")
        elif "task" in persisted:
            self.task = persisted["task"]
            self._loaded_fields.add("task")
        if "action" in persisted:
            self.action = persisted["action"]
            self._loaded_fields.add("action")
        elif "action" in persisted:
            self.action = persisted["action"]
            self._loaded_fields.add("action")
        if "detail" in persisted:
            self.detail = persisted["detail"]
            self._loaded_fields.add("detail")
        elif "detail" in persisted:
            self.detail = persisted["detail"]
            self._loaded_fields.add("detail")
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

        cascade_relations = []
        if action != "Delete":
            for relation_name, children, updater in cascade_relations:
                for index, child in enumerate(children):
                    child._teaql_attach_root(self._entity_root)
                    getattr(child, updater)(self)
                    try:
                        await child._teaql_save_within_graph(graph, scope)
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
        graph.after_commit(commit_entity)
        return self

    def update_id(self, value):
        self.id = value
        self._loaded_fields.add("id")
        self._entity_root.set(self._teaql_entity_key(), "id", Value.from_any(value))
        return self

    def update_action(self, value):
        self.action = value
        self._loaded_fields.add("action")
        self._entity_root.set(self._teaql_entity_key(), "action", Value.from_any(value))
        return self

    def update_detail(self, value):
        self.detail = value
        self._loaded_fields.add("detail")
        self._entity_root.set(self._teaql_entity_key(), "detail", Value.from_any(value))
        return self

    def update_version(self, value):
        self.version = value
        self._loaded_fields.add("version")
        self._entity_root.set(self._teaql_entity_key(), "version", Value.from_any(value))
        return self
    def update_task(self, value):
        self.task = getattr(value, "id", value) if value else None
        self._loaded_fields.add("task")
        self._entity_root.set(self._teaql_entity_key(), "task", Value.from_any(self.task))
        return self
