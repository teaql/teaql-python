class TeaQLNotLoadedError(RuntimeError):
    def __init__(self, root, access_path, break_point):
        self.root = root
        self.access_path = access_path
        self.break_point = break_point
        super().__init__(
            f"TeaQLNotLoadedError: root={root} access_path={access_path} "
            f"break_point={break_point} suggested_fix=select_{break_point}(...)"
        )


class ValueExpression:
    def __init__(self, value=None, error=None):
        self._value = value
        self._error = error

    def eval(self):
        if self._error is not None:
            raise self._error
        return self._value

    def or_if_null(self, fallback):
        value = self.eval()
        return fallback if value is None else value


class EntityExpression:
    def __init__(self, value, root=None, path="", error=None):
        self._value = value
        self._root = root or f"{type(value).__name__ if value is not None else 'Entity'}(null)"
        self._path = path
        self._error = error

    def eval(self):
        if self._error is not None:
            raise self._error
        return self._value

    def _path_for(self, field):
        return f"{self._path}.{field}" if self._path else field

    def _not_loaded(self, field):
        path = self._path_for(field)
        return TeaQLNotLoadedError(self._root, path, field)

    def _scalar(self, field, relation_id=False):
        if self._error is not None:
            return ValueExpression(error=self._error)
        if self._value is None:
            return ValueExpression(None)
        if field not in getattr(self._value, "_loaded_fields", set()):
            return ValueExpression(error=self._not_loaded(field))
        value = getattr(self._value, field)
        if relation_id and value is not None and not isinstance(value, (int, str)):
            value = getattr(value, "id", None)
        return ValueExpression(value)

    def _relation(self, field, expression_type):
        path = self._path_for(field)
        if self._error is not None:
            return expression_type(None, self._root, path, self._error)
        if self._value is None:
            return expression_type(None, self._root, path)
        if field not in getattr(self._value, "_loaded_fields", set()):
            return expression_type(None, self._root, path, self._not_loaded(field))
        value = getattr(self._value, field)
        if value is not None and isinstance(value, (int, str)):
            return expression_type(None, self._root, path, self._not_loaded(field))
        return expression_type(value, self._root, path)


class ListExpression:
    def __init__(self, values, root, path, item_expression, error=None):
        self._values = values
        self._root = root
        self._path = path
        self._item_expression = item_expression
        self._error = error

    def size(self):
        return ValueExpression(error=self._error) if self._error else ValueExpression(len(self._values))

    def first(self):
        return self.get(0)

    def get(self, index):
        path = f"{self._path}.get({index})"
        if self._error is not None:
            return self._item_expression(None, self._root, path, self._error)
        value = self._values[index] if 0 <= index < len(self._values) else None
        return self._item_expression(value, self._root, path)


class PlatformExpression(EntityExpression):
    def id(self):
        return self._scalar("id")
    def name(self):
        return self._scalar("name")
    def version(self):
        return self._scalar("version")
    def customer_order_list(self):
        path = self._path_for("customer_order_list")
        if self._error is not None:
            return ListExpression([], self._root, path, CustomerOrderExpression, self._error)
        if self._value is None:
            return ListExpression([], self._root, path, CustomerOrderExpression)
        if "customer_order_list" not in getattr(self._value, "_loaded_fields", set()):
            return ListExpression([], self._root, path, CustomerOrderExpression, self._not_loaded("customer_order_list"))
        return ListExpression(getattr(self._value, "_customer_order_list"), self._root, path, CustomerOrderExpression)
    pass

class CustomerOrderExpression(EntityExpression):
    def id(self):
        return self._scalar("id")
    def order_number(self):
        return self._scalar("orderNumber")
    def description(self):
        return self._scalar("description")
    def version(self):
        return self._scalar("version")
    def platform_id(self):
        return self._scalar("platform", relation_id=True)

    def platform(self):
        return self._relation("platform", PlatformExpression)
    def order_item_list(self):
        path = self._path_for("order_item_list")
        if self._error is not None:
            return ListExpression([], self._root, path, OrderItemExpression, self._error)
        if self._value is None:
            return ListExpression([], self._root, path, OrderItemExpression)
        if "order_item_list" not in getattr(self._value, "_loaded_fields", set()):
            return ListExpression([], self._root, path, OrderItemExpression, self._not_loaded("order_item_list"))
        return ListExpression(getattr(self._value, "_order_item_list"), self._root, path, OrderItemExpression)
    def payment_list(self):
        path = self._path_for("payment_list")
        if self._error is not None:
            return ListExpression([], self._root, path, PaymentExpression, self._error)
        if self._value is None:
            return ListExpression([], self._root, path, PaymentExpression)
        if "payment_list" not in getattr(self._value, "_loaded_fields", set()):
            return ListExpression([], self._root, path, PaymentExpression, self._not_loaded("payment_list"))
        return ListExpression(getattr(self._value, "_payment_list"), self._root, path, PaymentExpression)
    def shipment_list(self):
        path = self._path_for("shipment_list")
        if self._error is not None:
            return ListExpression([], self._root, path, ShipmentExpression, self._error)
        if self._value is None:
            return ListExpression([], self._root, path, ShipmentExpression)
        if "shipment_list" not in getattr(self._value, "_loaded_fields", set()):
            return ListExpression([], self._root, path, ShipmentExpression, self._not_loaded("shipment_list"))
        return ListExpression(getattr(self._value, "_shipment_list"), self._root, path, ShipmentExpression)
    pass

class OrderItemExpression(EntityExpression):
    def id(self):
        return self._scalar("id")
    def name(self):
        return self._scalar("name")
    def version(self):
        return self._scalar("version")
    def customer_order_id(self):
        return self._scalar("customerOrder", relation_id=True)

    def customer_order(self):
        return self._relation("customerOrder", CustomerOrderExpression)
    pass

class PaymentExpression(EntityExpression):
    def id(self):
        return self._scalar("id")
    def reference_code(self):
        return self._scalar("referenceCode")
    def version(self):
        return self._scalar("version")
    def customer_order_id(self):
        return self._scalar("customerOrder", relation_id=True)

    def customer_order(self):
        return self._relation("customerOrder", CustomerOrderExpression)
    def payment_attempt_list(self):
        path = self._path_for("payment_attempt_list")
        if self._error is not None:
            return ListExpression([], self._root, path, PaymentAttemptExpression, self._error)
        if self._value is None:
            return ListExpression([], self._root, path, PaymentAttemptExpression)
        if "payment_attempt_list" not in getattr(self._value, "_loaded_fields", set()):
            return ListExpression([], self._root, path, PaymentAttemptExpression, self._not_loaded("payment_attempt_list"))
        return ListExpression(getattr(self._value, "_payment_attempt_list"), self._root, path, PaymentAttemptExpression)
    pass

class PaymentAttemptExpression(EntityExpression):
    def id(self):
        return self._scalar("id")
    def reference_code(self):
        return self._scalar("referenceCode")
    def version(self):
        return self._scalar("version")
    def payment_id(self):
        return self._scalar("payment", relation_id=True)

    def payment(self):
        return self._relation("payment", PaymentExpression)
    pass

class ShipmentExpression(EntityExpression):
    def id(self):
        return self._scalar("id")
    def reference_code(self):
        return self._scalar("referenceCode")
    def version(self):
        return self._scalar("version")
    def customer_order_id(self):
        return self._scalar("customerOrder", relation_id=True)

    def customer_order(self):
        return self._relation("customerOrder", CustomerOrderExpression)
    pass

class E:
    @staticmethod
    def platform(value):
        entity_id = getattr(value, "id", None)
        return PlatformExpression(value, "Platform(id={})".format(entity_id))
    @staticmethod
    def customer_order(value):
        entity_id = getattr(value, "id", None)
        return CustomerOrderExpression(value, "CustomerOrder(id={})".format(entity_id))
    @staticmethod
    def order_item(value):
        entity_id = getattr(value, "id", None)
        return OrderItemExpression(value, "OrderItem(id={})".format(entity_id))
    @staticmethod
    def payment(value):
        entity_id = getattr(value, "id", None)
        return PaymentExpression(value, "Payment(id={})".format(entity_id))
    @staticmethod
    def payment_attempt(value):
        entity_id = getattr(value, "id", None)
        return PaymentAttemptExpression(value, "PaymentAttempt(id={})".format(entity_id))
    @staticmethod
    def shipment(value):
        entity_id = getattr(value, "id", None)
        return ShipmentExpression(value, "Shipment(id={})".format(entity_id))
    pass