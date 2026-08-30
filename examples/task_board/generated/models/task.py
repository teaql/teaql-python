from teaql.core.mutation import InsertCommand, UpdateCommand, DeleteCommand, MutationRequest
from teaql.core.value import Value

class Task:
    def __init__(self, **kwargs):
        self._action = "Update" if kwargs.get("id") else "Create"
        self._comment = None
        self.id = kwargs.get("id")
        self.name = kwargs.get("name")
        self.status = kwargs.get("status")
        self.platform = kwargs.get("platform")
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

        if getattr(self, "name", None) is not None:
            payload["name"] = Value.Text(self.name)

        if getattr(self, "status", None) is not None:
            payload["status"] = Value.I64(self.status)

        if getattr(self, "platform", None) is not None:
            payload["platform"] = Value.I64(self.platform)

        if getattr(self, "version", None) is not None:
            payload["version"] = Value.I64(self.version)


        if self._action == "Create":
            cmd = InsertCommand("Task", payload)
        elif self._action == "Update":
            cmd = UpdateCommand("Task", Value.from_any(getattr(self, "id", None)))
            for k, v in payload.items():
                if k != "id":
                    cmd.value(k, v)
        elif self._action == "Delete":
            cmd = DeleteCommand("Task", Value.from_any(getattr(self, "id", None)))


        req = MutationRequest(cmd)
        if self._comment:
            req.comment = self._comment

        return await service.mutate(context, req)