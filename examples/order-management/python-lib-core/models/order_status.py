from teaql.core.mutation import InsertCommand, UpdateCommand, DeleteCommand, MutationRequest
from teaql.core.value import Value

class OrderStatus:
    @classmethod
    def refer(cls, entity_id):
        return cls(id=entity_id)

    def __init__(self, **kwargs):
        self._action = "Update" if kwargs.get("id") else "Create"
        self._comment = None
        self._loaded_fields = set(kwargs.keys())
        self.id = kwargs.get("id")
        self.name = kwargs.get("name")
        self.code = kwargs.get("code")
        self.color = kwargs.get("color")
        self.displayOrder = kwargs.get("displayOrder")
        self.commercePlatform = kwargs.get("commercePlatform")
        self.version = kwargs.get("version")
        self._customer_order_list = []
        self._loaded_fields.add("customer_order_list")
    def mark_for_deletion(self):
        self._action = "Delete"
        return self

    def audit_as(self, comment: str):
        self._comment = comment
        return self

    async def save(self, context):
        if not self._comment:
            raise Exception("Security audit failure: audit_as() must be called before save()")

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
            payload["display_order"] = Value.Object(self.displayOrder)
        if getattr(self, "commercePlatform", None) is not None:
            payload["commerce_platform"] = Value.Object(self.commercePlatform)
        if getattr(self, "version", None) is not None:
            payload["version"] = Value.I64(self.version)

        action = self._action
        if action == "Create":
            cmd = InsertCommand("OrderStatus", payload)
        elif self._action == "Update":
            cmd = UpdateCommand(
                "OrderStatus",
                Value.from_any(getattr(self, "id", None)),
                getattr(self, "version", None),
            )
            for k, v in payload.items():
                if k not in ("id", "version"):
                    cmd.value(k, v)
        elif self._action == "Delete":
            cmd = DeleteCommand(
                "OrderStatus",
                Value.from_any(getattr(self, "id", None)),
                getattr(self, "version", None),
            )


        req = MutationRequest(cmd)
        if self._comment:
            req.comment = self._comment

        service = context.require_resource("dataService")
        result = await service.mutate(context, req)
        if action == "Create":
            self.id = result["id"]
            self.version = result.get("version")
            self._action = "Update"
        elif action == "Update":
            self.version = result.get("version", getattr(self, "version", None))

        cascade_relations = []
        cascade_relations.append((self._customer_order_list, "update_status"))
        if action != "Delete":
            for children, updater in cascade_relations:
                for child in children:
                    getattr(child, updater)(self)
                    child.audit_as(self._comment)
                    await child.save(context)
        return result

    def update_id(self, value):
        self.id = value
        self._loaded_fields.add("id")
        return self

    def update_name(self, value):
        self.name = value
        self._loaded_fields.add("name")
        return self

    def update_code(self, value):
        self.code = value
        self._loaded_fields.add("code")
        return self

    def update_color(self, value):
        self.color = value
        self._loaded_fields.add("color")
        return self

    def update_display_order(self, value):
        self.displayOrder = value
        self._loaded_fields.add("displayOrder")
        return self

    def update_version(self, value):
        self.version = value
        self._loaded_fields.add("version")
        return self
    def update_commerce_platform(self, value):
        self.commercePlatform = getattr(value, "id", value) if value else None
        self._loaded_fields.add("commercePlatform")
        return self

    def customer_order_list(self) -> list:
        return self._customer_order_list