from teaql.core.mutation import InsertCommand, UpdateCommand, DeleteCommand, MutationRequest
from teaql.core import MutationIntent
from teaql.core.value import Value
from teaql.runtime import CheckException, CheckResult, EntityKey, EntityRoot, ObjectLocation
import itertools


class Platform:
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
        if "founded" in kwargs and "founded" not in kwargs:
            kwargs["founded"] = kwargs.pop("founded")
        if "user_email" in kwargs and "userEmail" not in kwargs:
            kwargs["userEmail"] = kwargs.pop("user_email")
        if "version" in kwargs and "version" not in kwargs:
            kwargs["version"] = kwargs.pop("version")
        self._action = "Update" if kwargs.get("id") else "Create"
        self._comment = None
        self._loaded_fields = set(kwargs.keys())
        self.id = kwargs.get("id")

        self.name = kwargs.get("name")

        self.founded = kwargs.get("founded")

        self.userEmail = kwargs.get("userEmail")

        self.version = kwargs.get("version")

        self._task_status_list = kwargs.get("task_status_list", [])
        if "task_status_list" in kwargs or kwargs.get("id") is None:
            self._loaded_fields.add("task_status_list")
        self._task_list = kwargs.get("task_list", [])
        if "task_list" in kwargs or kwargs.get("id") is None:
            self._loaded_fields.add("task_list")
        if self._task_status_list:
            from models.task_status import TaskStatus
            self._task_status_list = [
                item if isinstance(item, TaskStatus) else TaskStatus(_entity_root=self._entity_root, **item)
                for item in self._task_status_list
            ]
        if self._task_list:
            from models.task import Task
            self._task_list = [
                item if isinstance(item, Task) else Task(_entity_root=self._entity_root, **item)
                for item in self._task_list
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
        return EntityKey("Platform", self._ledger_id)

    def _teaql_attach_root(self, root):
        key = self._teaql_entity_key()
        if self._entity_root is not root and self._entity_root.has_pending(key):
            root.merge_entity_from(self._entity_root, key)
            self._entity_root = root
        for child in self._task_status_list:
            child._teaql_attach_root(root)
        for child in self._task_list:
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
            self.id = int(await allocator("Platform"))
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
        for child in self._task_status_list:
            child._teaql_attach_root(self._entity_root)
            await child._teaql_reserve_graph_ids(graph, visited)
        for child in self._task_list:
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

        if "name" in self._loaded_fields:
            payload["name"] = Value.Text(self.name)

        if "founded" in self._loaded_fields:
            payload["founded"] = Value.DateTime(self.founded)

        if "userEmail" in self._loaded_fields:
            payload["user_email"] = Value.Text(self.userEmail)

        if "version" in self._loaded_fields:
            payload["version"] = Value.I64(self.version)

        action = self._action
        if action == "Update":
            ledger = dict(self._entity_root.current_change_set().changes()).get(self._teaql_entity_key(), {})
            payload = {field: value for field, value in ledger.items() if field not in ("id", "version")}
        if action == "Create":
            cmd = InsertCommand("Platform", payload)
        elif action == "Update":
            original_version = self._entity_root.original_version(self._teaql_entity_key())
            cmd = UpdateCommand("Platform", Value.from_any(getattr(self, "id", None)),
                original_version if original_version is not None else getattr(self, "version", None))
            for key, value in payload.items():
                if key not in ("id", "version"): cmd.value(key, value)
        else:
            original_version = self._entity_root.original_version(self._teaql_entity_key())
            cmd = DeleteCommand("Platform", Value.from_any(getattr(self, "id", None)),
                original_version if original_version is not None else getattr(self, "version", None))
        return action, cmd

    def _teaql_preflight_graph(self, graph):
        context = graph.context
        if self._action != "Update" or self._entity_root.has_pending(self._teaql_entity_key()):
            if self._action == "Update":
                if "id" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("id"), message="Mutation requires a fully loaded entity")])
                if "name" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("name"), message="Mutation requires a fully loaded entity")])
                if "founded" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("founded"), message="Mutation requires a fully loaded entity")])
                if "userEmail" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("user_email"), message="Mutation requires a fully loaded entity")])
                if "version" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("version"), message="Mutation requires a fully loaded entity")])
            _action, cmd = self._teaql_build_command()
            try:
                context.preflight_mutation(cmd)
            finally:
                for field, value in getattr(cmd, "values", {}).items():
                    if field not in ("id", "version"):
                        self._entity_root.set(self._teaql_entity_key(), field, value)
        for index, child in enumerate(self._task_status_list):
            child._teaql_attach_root(self._entity_root)
            current = getattr(child, "platform", None)
            if getattr(current, "id", current) != self.id:
                child.update_platform(self)
            try:
                child._teaql_preflight_graph(graph)
            except CheckException as error:
                prefix = ObjectLocation().property("task_status_list").index(index)
                raise CheckException([
                    CheckResult(v.rule_id, v.location.prefixed_by(prefix), v.input_value, v.system_value, v.message)
                    for v in error.violations
                ]) from error
        for index, child in enumerate(self._task_list):
            child._teaql_attach_root(self._entity_root)
            current = getattr(child, "platform", None)
            if getattr(current, "id", current) != self.id:
                child.update_platform(self)
            try:
                child._teaql_preflight_graph(graph)
            except CheckException as error:
                prefix = ObjectLocation().property("task_list").index(index)
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
                "Mutation provider did not return authoritative persisted state for Platform"
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
        if "founded" in persisted:
            self.founded = persisted["founded"]
            self._loaded_fields.add("founded")
        elif "founded" in persisted:
            self.founded = persisted["founded"]
            self._loaded_fields.add("founded")
        if "user_email" in persisted:
            self.userEmail = persisted["user_email"]
            self._loaded_fields.add("userEmail")
        elif "userEmail" in persisted:
            self.userEmail = persisted["userEmail"]
            self._loaded_fields.add("userEmail")
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
        cascade_relations.append(("task_status_list", self._task_status_list, "update_platform", "platform"))
        cascade_relations.append(("task_list", self._task_list, "update_platform", "platform"))
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

    def update_name(self, value):
        self.name = value
        self._loaded_fields.add("name")
        self._entity_root.set(self._teaql_entity_key(), "name", Value.from_any(value))
        return self

    def update_founded(self, value):
        self.founded = value
        self._loaded_fields.add("founded")
        self._entity_root.set(self._teaql_entity_key(), "founded", Value.from_any(value))
        return self

    def update_user_email(self, value):
        self.userEmail = value
        self._loaded_fields.add("userEmail")
        self._entity_root.set(self._teaql_entity_key(), "user_email", Value.from_any(value))
        return self

    def update_version(self, value):
        self.version = value
        self._loaded_fields.add("version")
        self._entity_root.set(self._teaql_entity_key(), "version", Value.from_any(value))
        return self
    def task_status_list(self) -> list:
        self._loaded_fields.add("task_status_list")
        return self._task_status_list

    def task_list(self) -> list:
        self._loaded_fields.add("task_list")
        return self._task_list
