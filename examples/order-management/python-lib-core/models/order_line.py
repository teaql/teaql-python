from teaql.core.mutation import InsertCommand, UpdateCommand, DeleteCommand, MutationRequest
from teaql.core.value import Value

class OrderLine:
    @classmethod
    def refer(cls, entity_id):
        return cls(id=entity_id)

    def __init__(self, **kwargs):
        self._action = "Update" if kwargs.get("id") else "Create"
        self._comment = None
        self._loaded_fields = set(kwargs.keys())
        self.id = kwargs.get("id")
        self.customerOrder = kwargs.get("customerOrder")
        self.product = kwargs.get("product")
        self.productName = kwargs.get("productName")
        self.sku = kwargs.get("sku")
        self.quantity = kwargs.get("quantity")
        self.commercePlatform = kwargs.get("commercePlatform")
        self.createTime = kwargs.get("createTime")
        self.version = kwargs.get("version")
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
        if getattr(self, "customerOrder", None) is not None:
            payload["customer_order"] = Value.Object(self.customerOrder)
        if getattr(self, "product", None) is not None:
            payload["product"] = Value.Object(self.product)
        if getattr(self, "productName", None) is not None:
            payload["product_name"] = Value.Text(self.productName)
        if getattr(self, "sku", None) is not None:
            payload["sku"] = Value.Text(self.sku)
        if getattr(self, "quantity", None) is not None:
            payload["quantity"] = Value.Object(self.quantity)
        if getattr(self, "commercePlatform", None) is not None:
            payload["commerce_platform"] = Value.Object(self.commercePlatform)
        if getattr(self, "createTime", None) is not None:
            payload["create_time"] = Value.Date(self.createTime)
        if getattr(self, "version", None) is not None:
            payload["version"] = Value.I64(self.version)

        action = self._action
        if action == "Create":
            cmd = InsertCommand("OrderLine", payload)
        elif self._action == "Update":
            cmd = UpdateCommand(
                "OrderLine",
                Value.from_any(getattr(self, "id", None)),
                getattr(self, "version", None),
            )
            for k, v in payload.items():
                if k not in ("id", "version"):
                    cmd.value(k, v)
        elif self._action == "Delete":
            cmd = DeleteCommand(
                "OrderLine",
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

    def update_product_name(self, value):
        self.productName = value
        self._loaded_fields.add("productName")
        return self

    def update_sku(self, value):
        self.sku = value
        self._loaded_fields.add("sku")
        return self

    def update_quantity(self, value):
        self.quantity = value
        self._loaded_fields.add("quantity")
        return self

    def update_create_time(self, value):
        self.createTime = value
        self._loaded_fields.add("createTime")
        return self

    def update_version(self, value):
        self.version = value
        self._loaded_fields.add("version")
        return self
    def update_customer_order(self, value):
        self.customerOrder = getattr(value, "id", value) if value else None
        self._loaded_fields.add("customerOrder")
        return self


    def update_product(self, value):
        self.product = getattr(value, "id", value) if value else None
        self._loaded_fields.add("product")
        return self


    def update_commerce_platform(self, value):
        self.commercePlatform = getattr(value, "id", value) if value else None
        self._loaded_fields.add("commercePlatform")
        return self

