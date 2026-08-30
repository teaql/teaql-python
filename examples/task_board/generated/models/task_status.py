from teaql.core.mutation import InsertCommand, UpdateCommand, DeleteCommand, MutationRequest
from teaql.core.value import Value

class TaskStatus:
    def __init__(self, **kwargs):
        self._action = "Update" if kwargs.get("id") else "Create"
        self._comment = None
        self.id = kwargs.get("id")
        self.name = kwargs.get("name")
        self.code = kwargs.get("code")
        self.color = kwargs.get("color")
        self.displayOrder = kwargs.get("displayOrder")
        self.progress = kwargs.get("progress")
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

        if getattr(self, "code", None) is not None:
            payload["code"] = Value.Text(self.code)

        if getattr(self, "color", None) is not None:
            payload["color"] = Value.Text(self.color)

        if getattr(self, "displayOrder", None) is not None:
            payload["display_order"] = Value.I64(self.displayOrder)

        if getattr(self, "progress", None) is not None:
            payload["progress"] = Value.I64(self.progress)

        if getattr(self, "platform", None) is not None:
            payload["platform"] = Value.I64(self.platform)

        if getattr(self, "version", None) is not None:
            payload["version"] = Value.I64(self.version)


        if self._action == "Create":
            cmd = InsertCommand("TaskStatus", payload)
        elif self._action == "Update":
            cmd = UpdateCommand("TaskStatus", Value.from_any(getattr(self, "id", None)))
            for k, v in payload.items():
                if k != "id":
                    cmd.value(k, v)
        elif self._action == "Delete":
            cmd = DeleteCommand("TaskStatus", Value.from_any(getattr(self, "id", None)))


        req = MutationRequest(cmd)
        if self._comment:
            req.comment = self._comment

        return await service.mutate(context, req)