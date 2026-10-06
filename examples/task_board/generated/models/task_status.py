from teaql.core.mutation import InsertCommand, UpdateCommand, DeleteCommand, MutationRequest
from teaql.core.entity import _LoadedScalarSnapshot
from teaql.core import MutationIntent
from teaql.core.value import Value
from teaql.runtime import CheckException, CheckResult, EntityKey, EntityRoot, ObjectLocation
import itertools
from models.platform import Platform


class TaskStatus:
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
        if "code" in kwargs and "code" not in kwargs:
            kwargs["code"] = kwargs.pop("code")
        if "color" in kwargs and "color" not in kwargs:
            kwargs["color"] = kwargs.pop("color")
        if "display_order" in kwargs and "displayOrder" not in kwargs:
            kwargs["displayOrder"] = kwargs.pop("display_order")
        if "progress" in kwargs and "progress" not in kwargs:
            kwargs["progress"] = kwargs.pop("progress")
        if "platform" in kwargs and "platform" not in kwargs:
            kwargs["platform"] = kwargs.pop("platform")
        if "version" in kwargs and "version" not in kwargs:
            kwargs["version"] = kwargs.pop("version")
        self._action = "Update" if kwargs.get("id") else "Create"
        self._comment = None
        self._loaded_fields = set(kwargs.keys())
        self.id = kwargs.get("id")

        self.name = kwargs.get("name")

        self.code = kwargs.get("code")

        self.color = kwargs.get("color")

        self.displayOrder = kwargs.get("displayOrder")

        self.progress = kwargs.get("progress")

        self.platform = kwargs.get("platform")

        self.version = kwargs.get("version")

        if isinstance(self.platform, dict):
            self.platform = Platform(**self.platform)
        self._task_list = kwargs.get("task_list", [])
        if "task_list" in kwargs or kwargs.get("id") is None:
            self._loaded_fields.add("task_list")
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
        self._teaql_loaded_snapshot = _LoadedScalarSnapshot(
            self._teaql_scalar_payload() if self._action == "Update" else {})

    def _teaql_entity_key(self):
        return EntityKey("TaskStatus", self._ledger_id)

    def _teaql_attach_root(self, root):
        key = self._teaql_entity_key()
        if self._entity_root is not root and self._entity_root.has_pending(key):
            root.merge_entity_from(self._entity_root, key)
            self._entity_root = root
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
            self.id = int(await allocator("TaskStatus"))
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
        for child in self._task_list:
            child._teaql_attach_root(self._entity_root)
            await child._teaql_reserve_graph_ids(graph, visited)

    async def _teaql_preflight_and_save(self, graph):
        await self._teaql_reserve_graph_ids(graph, set())
        self._teaql_preflight_graph(graph)
        return await self._teaql_save_within_graph(graph)

    def _teaql_scalar_payload(self):
        payload = {}
        if "id" in self._loaded_fields:
            payload["id"] = Value.I64(self.id)

        if "name" in self._loaded_fields:
            payload["name"] = Value.Text(self.name)

        if "code" in self._loaded_fields:
            payload["code"] = Value.Text(self.code)

        if "color" in self._loaded_fields:
            payload["color"] = Value.Text(self.color)

        if "displayOrder" in self._loaded_fields:
            payload["display_order"] = Value.Decimal(self.displayOrder)

        if "progress" in self._loaded_fields:
            payload["progress"] = Value.Decimal(self.progress)

        if "platform" in self._loaded_fields:
            reference = self.platform
            reference_id = getattr(reference, "id", reference)
            payload["platform"] = (Value.Object(reference)
                if reference is not None and hasattr(reference, "id") and reference_id is None
                else Value.I64(reference_id))

        if "version" in self._loaded_fields:
            payload["version"] = Value.I64(self.version)

        return payload

    def _teaql_build_command(self):
        payload = self._teaql_scalar_payload()
        action = self._action
        if action == "Update":
            ledger = dict(self._entity_root.current_change_set().changes()).get(self._teaql_entity_key(), {})
            payload = {field: value for field, value in ledger.items() if field not in ("id", "version")}
        if action == "Create":
            cmd = InsertCommand("TaskStatus", payload)
        elif action == "Update":
            original_version = self._entity_root.original_version(self._teaql_entity_key())
            cmd = UpdateCommand("TaskStatus", Value.from_any(getattr(self, "id", None)),
                original_version if original_version is not None else getattr(self, "version", None))
            for key, value in payload.items():
                if key not in ("id", "version"): cmd.value(key, value)
        else:
            original_version = self._entity_root.original_version(self._teaql_entity_key())
            cmd = DeleteCommand("TaskStatus", Value.from_any(getattr(self, "id", None)),
                original_version if original_version is not None else getattr(self, "version", None))
        if action != "Create":
            cmd.old_values = self._teaql_loaded_snapshot.business_values()
        return action, cmd

    def _teaql_preflight_graph(self, graph):
        context = graph.context
        if self._action != "Update" or self._entity_root.has_pending(self._teaql_entity_key()):
            if self._action == "Update":
                if "id" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("id"), message="Mutation requires a fully loaded entity")])
                if "name" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("name"), message="Mutation requires a fully loaded entity")])
                if "code" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("code"), message="Mutation requires a fully loaded entity")])
                if "color" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("color"), message="Mutation requires a fully loaded entity")])
                if "displayOrder" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("display_order"), message="Mutation requires a fully loaded entity")])
                if "progress" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("progress"), message="Mutation requires a fully loaded entity")])
                if "platform" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("platform"), message="Mutation requires a fully loaded entity")])
                if "version" not in self._loaded_fields:
                    raise CheckException([CheckResult("invalid_type", ObjectLocation().property("version"), message="Mutation requires a fully loaded entity")])
            _action, cmd = self._teaql_build_command()
            try:
                context.preflight_mutation(cmd)
            finally:
                for field, value in getattr(cmd, "values", {}).items():
                    if field not in ("id", "version"):
                        self._entity_root.set(self._teaql_entity_key(), field, value)
        for index, child in enumerate(self._task_list):
            child._teaql_attach_root(self._entity_root)
            current = getattr(child, "status", None)
            if getattr(current, "id", current) != self.id:
                child.update_status(self)
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
                "Mutation provider did not return authoritative persisted state for TaskStatus"
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
        if "code" in persisted:
            self.code = persisted["code"]
            self._loaded_fields.add("code")
        elif "code" in persisted:
            self.code = persisted["code"]
            self._loaded_fields.add("code")
        if "color" in persisted:
            self.color = persisted["color"]
            self._loaded_fields.add("color")
        elif "color" in persisted:
            self.color = persisted["color"]
            self._loaded_fields.add("color")
        if "display_order" in persisted:
            self.displayOrder = persisted["display_order"]
            self._loaded_fields.add("displayOrder")
        elif "displayOrder" in persisted:
            self.displayOrder = persisted["displayOrder"]
            self._loaded_fields.add("displayOrder")
        if "progress" in persisted:
            self.progress = persisted["progress"]
            self._loaded_fields.add("progress")
        elif "progress" in persisted:
            self.progress = persisted["progress"]
            self._loaded_fields.add("progress")
        if "platform" in persisted:
            self.platform = persisted["platform"]
            self._loaded_fields.add("platform")
        elif "platform" in persisted:
            self.platform = persisted["platform"]
            self._loaded_fields.add("platform")
        if "version" in persisted:
            self.version = persisted["version"]
            self._loaded_fields.add("version")
        elif "version" in persisted:
            self.version = persisted["version"]
            self._loaded_fields.add("version")
        committed_snapshot = _LoadedScalarSnapshot(self._teaql_scalar_payload())
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
            self._teaql_loaded_snapshot = committed_snapshot
            self._entity_root.clear_entity(new_key)
            if getattr(self, "version", None) is not None:
                self._entity_root.accept_committed_version(new_key, int(self.version))
        graph.after_commit(commit_entity)
        return self

    async def _teaql_save_children(self, graph, scope):
        cascade_relations = []
        cascade_relations.append(("task_list", self._task_list, "update_status", "status"))
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

    def update_code(self, value):
        self.code = value
        self._loaded_fields.add("code")
        self._entity_root.set(self._teaql_entity_key(), "code", Value.from_any(value))
        return self

    def update_color(self, value):
        self.color = value
        self._loaded_fields.add("color")
        self._entity_root.set(self._teaql_entity_key(), "color", Value.from_any(value))
        return self

    def update_display_order(self, value):
        self.displayOrder = value
        self._loaded_fields.add("displayOrder")
        self._entity_root.set(self._teaql_entity_key(), "display_order", Value.from_any(value))
        return self

    def update_progress(self, value):
        self.progress = value
        self._loaded_fields.add("progress")
        self._entity_root.set(self._teaql_entity_key(), "progress", Value.from_any(value))
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

    def task_list(self) -> list:
        self._loaded_fields.add("task_list")
        return self._task_list
