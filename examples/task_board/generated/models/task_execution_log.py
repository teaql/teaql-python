from teaql.core.mutation import InsertCommand, UpdateCommand, DeleteCommand, MutationRequest
from teaql.core.value import Value

class TaskExecutionLog:
    def __init__(self, **kwargs):
        self._action = "Update" if kwargs.get("id") else "Create"
        self._comment = None
        self.id = kwargs.get("id")
        self.task = kwargs.get("task")
        self.action = kwargs.get("action")
        self.detail = kwargs.get("detail")
        self.version = kwargs.get("version")
        for k, v in kwargs.items():
            if not hasattr(self, k):
                setattr(self, k, v)

    def mark_for_deletion(self):
        self._action = "Delete"
        return self

    def audit_as(self, comment: str):
        self._comment = comment
        return self

    async def save(self, context, service):
        payload = {}
        if getattr(self, "id", None) is not None:
            payload["id"] = Value.I64(self.id)

        if getattr(self, "task", None) is not None:
            payload["task"] = Value.I64(self.task)

        if getattr(self, "action", None) is not None:
            payload["action"] = Value.Text(self.action)

        if getattr(self, "detail", None) is not None:
            payload["detail"] = Value.Text(self.detail)

        if getattr(self, "version", None) is not None:
            payload["version"] = Value.I64(self.version)


        if self._action == "Create":
            cmd = InsertCommand("TaskExecutionLog", payload)
        elif self._action == "Update":
            cmd = UpdateCommand("TaskExecutionLog", Value.from_any(getattr(self, "id", None)))
            for k, v in payload.items():
                if k != "id":
                    cmd.value(k, v)
        elif self._action == "Delete":
            cmd = DeleteCommand("TaskExecutionLog", Value.from_any(getattr(self, "id", None)))


        req = MutationRequest(cmd)
        if self._comment:
            req.comment = self._comment

        return await service.mutate(context, req)