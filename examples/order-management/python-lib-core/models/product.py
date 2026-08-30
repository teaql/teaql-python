from teaql.core.mutation import InsertCommand, UpdateCommand, DeleteCommand, MutationRequest
from teaql.core.value import Value

class Product:
    @classmethod
    def refer(cls, entity_id):
        return cls(id=entity_id)

    def __init__(self, **kwargs):
        self._action = "Update" if kwargs.get("id") else "Create"
        self._comment = None
        self._loaded_fields = set(kwargs.keys())
        self.id = kwargs.get("id")
        self.name = kwargs.get("name")
        self.sku = kwargs.get("sku")
        self.imageUrl = kwargs.get("imageUrl")
        self.commercePlatform = kwargs.get("commercePlatform")
        self.createTime = kwargs.get("createTime")
        self.updateTime = kwargs.get("updateTime")
        self.version = kwargs.get("version")
        self._order_line_list = []
        self._loaded_fields.add("order_line_list")
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
        if getattr(self, "sku", None) is not None:
            payload["sku"] = Value.Text(self.sku)
        if getattr(self, "imageUrl", None) is not None:
            payload["image_url"] = Value.Text(self.imageUrl)
        if getattr(self, "commercePlatform", None) is not None:
            payload["commerce_platform"] = Value.Object(self.commercePlatform)
        if getattr(self, "createTime", None) is not None:
            payload["create_time"] = Value.Date(self.createTime)
        if getattr(self, "updateTime", None) is not None:
            payload["update_time"] = Value.Date(self.updateTime)
        if getattr(self, "version", None) is not None:
            payload["version"] = Value.I64(self.version)

        action = self._action
        if action == "Create":
            cmd = InsertCommand("Product", payload)
        elif self._action == "Update":
            cmd = UpdateCommand(
                "Product",
                Value.from_any(getattr(self, "id", None)),
                getattr(self, "version", None),
            )
            for k, v in payload.items():
                if k not in ("id", "version"):
                    cmd.value(k, v)
        elif self._action == "Delete":
            cmd = DeleteCommand(
                "Product",
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
        cascade_relations.append((self._order_line_list, "update_product"))
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

    def update_sku(self, value):
        self.sku = value
        self._loaded_fields.add("sku")
        return self

    def update_image_url(self, value):
        self.imageUrl = value
        self._loaded_fields.add("imageUrl")
        return self

    def update_create_time(self, value):
        self.createTime = value
        self._loaded_fields.add("createTime")
        return self

    def update_update_time(self, value):
        self.updateTime = value
        self._loaded_fields.add("updateTime")
        return self

    def update_version(self, value):
        self.version = value
        self._loaded_fields.add("version")
        return self
    def update_commerce_platform(self, value):
        self.commercePlatform = getattr(value, "id", value) if value else None
        self._loaded_fields.add("commercePlatform")
        return self

    def order_line_list(self) -> list:
        return self._order_line_list