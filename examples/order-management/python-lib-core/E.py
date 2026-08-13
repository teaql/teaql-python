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

    def or_else(self, fallback):
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

    def __getattr__(self, method_name):
        def access():
            path = f"{self._path}.{method_name}" if self._path else method_name
            if self._error is not None:
                return ValueExpression(error=self._error)
            if self._value is None:
                return ValueExpression(None)
            field_name = method_name[:-3] if method_name.endswith("_id") else method_name
            loaded = getattr(self._value, "_loaded_fields", set())
            if field_name not in loaded and method_name not in loaded:
                return ValueExpression(error=TeaQLNotLoadedError(self._root, path, method_name))
            value = getattr(self._value, field_name)
            if callable(value):
                value = value()
            if isinstance(value, list):
                return ListExpression(value, self._root, path)
            return ValueExpression(value)
        return access


class ListExpression:
    def __init__(self, values, root, path):
        self._values = values
        self._root = root
        self._path = path

    def size(self):
        return ValueExpression(len(self._values))

    def first(self):
        return self.get(0)

    def get(self, index):
        value = self._values[index] if 0 <= index < len(self._values) else None
        return EntityExpression(value, self._root, f"{self._path}.get({index})")


class E:
    @staticmethod
    def commerce_platform(value):
        entity_id = getattr(value, "id", None)
        return EntityExpression(value, "CommercePlatform(id={})".format(entity_id))
    @staticmethod
    def customer(value):
        entity_id = getattr(value, "id", None)
        return EntityExpression(value, "Customer(id={})".format(entity_id))
    @staticmethod
    def order_status(value):
        entity_id = getattr(value, "id", None)
        return EntityExpression(value, "OrderStatus(id={})".format(entity_id))
    @staticmethod
    def customer_order(value):
        entity_id = getattr(value, "id", None)
        return EntityExpression(value, "CustomerOrder(id={})".format(entity_id))
    @staticmethod
    def product(value):
        entity_id = getattr(value, "id", None)
        return EntityExpression(value, "Product(id={})".format(entity_id))
    @staticmethod
    def order_line(value):
        entity_id = getattr(value, "id", None)
        return EntityExpression(value, "OrderLine(id={})".format(entity_id))
    @staticmethod
    def order_search_preset(value):
        entity_id = getattr(value, "id", None)
        return EntityExpression(value, "OrderSearchPreset(id={})".format(entity_id))
    pass