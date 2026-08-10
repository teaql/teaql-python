from teaql.core.mutation import InsertCommand, UpdateCommand, DeleteCommand, MutationRequest
from teaql.core.value import Value

class Platform:
    def __init__(self, **kwargs):
        self._action = "Update" if kwargs.get("id") else "Create"
        self._comment = None
        self.id = kwargs.get("id")
        self.name = kwargs.get("name")
        self.founded = kwargs.get("founded")
        self.userEmail = kwargs.get("userEmail")
        self.version = kwargs.get("version")
        for k, v in kwargs.items():
            if not hasattr(self, k):
                setattr(self, k, v)

    def mark_as_deleted(self):
        self._action = "Delete"
        return self

    def audit_as(self, comment: str):
        self._comment = comment
        return self

    async def save(self, ctx, service):
        payload = {}
        if getattr(self, "id", None) is not None:
            payload["id"] = Value.I64(self.id)

        if getattr(self, "name", None) is not None:
            payload["name"] = Value.Text(self.name)

        if getattr(self, "founded", None) is not None:
            payload["founded"] = Value.I64(self.founded)

        if getattr(self, "userEmail", None) is not None:
            payload["user_email"] = Value.Text(self.userEmail)

        if getattr(self, "version", None) is not None:
            payload["version"] = Value.I64(self.version)


        if self._action == "Create":
            cmd = InsertCommand("Platform", payload)
        elif self._action == "Update":
            cmd = UpdateCommand("Platform", Value.from_any(getattr(self, "id", None)))
            for k, v in payload.items():
                if k != "id":
                    cmd.value(k, v)
        elif self._action == "Delete":
            cmd = DeleteCommand("Platform", Value.from_any(getattr(self, "id", None)))


        req = MutationRequest(cmd)
        if self._comment:
            req.comment = self._comment

        return await service.mutate(ctx, req)