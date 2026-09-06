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


class CommercePlatformExpression(EntityExpression):
    def id(self):
        return self._scalar("id")
    def name(self):
        return self._scalar("name")
    def create_time(self):
        return self._scalar("createTime")
    def update_time(self):
        return self._scalar("updateTime")
    def version(self):
        return self._scalar("version")
    def customer_list(self):
        path = self._path_for("customer_list")
        if self._error is not None:
            return ListExpression([], self._root, path, CustomerExpression, self._error)
        if self._value is None:
            return ListExpression([], self._root, path, CustomerExpression)
        if "customer_list" not in getattr(self._value, "_loaded_fields", set()):
            return ListExpression([], self._root, path, CustomerExpression, self._not_loaded("customer_list"))
        return ListExpression(getattr(self._value, "_customer_list"), self._root, path, CustomerExpression)
    def order_status_list(self):
        path = self._path_for("order_status_list")
        if self._error is not None:
            return ListExpression([], self._root, path, OrderStatusExpression, self._error)
        if self._value is None:
            return ListExpression([], self._root, path, OrderStatusExpression)
        if "order_status_list" not in getattr(self._value, "_loaded_fields", set()):
            return ListExpression([], self._root, path, OrderStatusExpression, self._not_loaded("order_status_list"))
        return ListExpression(getattr(self._value, "_order_status_list"), self._root, path, OrderStatusExpression)
    def customer_order_list(self):
        path = self._path_for("customer_order_list")
        if self._error is not None:
            return ListExpression([], self._root, path, CustomerOrderExpression, self._error)
        if self._value is None:
            return ListExpression([], self._root, path, CustomerOrderExpression)
        if "customer_order_list" not in getattr(self._value, "_loaded_fields", set()):
            return ListExpression([], self._root, path, CustomerOrderExpression, self._not_loaded("customer_order_list"))
        return ListExpression(getattr(self._value, "_customer_order_list"), self._root, path, CustomerOrderExpression)
    def product_list(self):
        path = self._path_for("product_list")
        if self._error is not None:
            return ListExpression([], self._root, path, ProductExpression, self._error)
        if self._value is None:
            return ListExpression([], self._root, path, ProductExpression)
        if "product_list" not in getattr(self._value, "_loaded_fields", set()):
            return ListExpression([], self._root, path, ProductExpression, self._not_loaded("product_list"))
        return ListExpression(getattr(self._value, "_product_list"), self._root, path, ProductExpression)
    def order_line_list(self):
        path = self._path_for("order_line_list")
        if self._error is not None:
            return ListExpression([], self._root, path, OrderLineExpression, self._error)
        if self._value is None:
            return ListExpression([], self._root, path, OrderLineExpression)
        if "order_line_list" not in getattr(self._value, "_loaded_fields", set()):
            return ListExpression([], self._root, path, OrderLineExpression, self._not_loaded("order_line_list"))
        return ListExpression(getattr(self._value, "_order_line_list"), self._root, path, OrderLineExpression)
    def order_search_preset_list(self):
        path = self._path_for("order_search_preset_list")
        if self._error is not None:
            return ListExpression([], self._root, path, OrderSearchPresetExpression, self._error)
        if self._value is None:
            return ListExpression([], self._root, path, OrderSearchPresetExpression)
        if "order_search_preset_list" not in getattr(self._value, "_loaded_fields", set()):
            return ListExpression([], self._root, path, OrderSearchPresetExpression, self._not_loaded("order_search_preset_list"))
        return ListExpression(getattr(self._value, "_order_search_preset_list"), self._root, path, OrderSearchPresetExpression)
    pass

class CustomerExpression(EntityExpression):
    def id(self):
        return self._scalar("id")
    def name(self):
        return self._scalar("name")
    def email(self):
        return self._scalar("email")
    def create_time(self):
        return self._scalar("createTime")
    def update_time(self):
        return self._scalar("updateTime")
    def version(self):
        return self._scalar("version")
    def commerce_platform_id(self):
        return self._scalar("commercePlatform", relation_id=True)

    def commerce_platform(self):
        return self._relation("commercePlatform", CommercePlatformExpression)
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

class OrderStatusExpression(EntityExpression):
    def id(self):
        return self._scalar("id")
    def name(self):
        return self._scalar("name")
    def code(self):
        return self._scalar("code")
    def color(self):
        return self._scalar("color")
    def display_order(self):
        return self._scalar("displayOrder")
    def version(self):
        return self._scalar("version")
    def commerce_platform_id(self):
        return self._scalar("commercePlatform", relation_id=True)

    def commerce_platform(self):
        return self._relation("commercePlatform", CommercePlatformExpression)
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
    def order_date(self):
        return self._scalar("orderDate")
    def total_amount(self):
        return self._scalar("totalAmount")
    def create_time(self):
        return self._scalar("createTime")
    def update_time(self):
        return self._scalar("updateTime")
    def version(self):
        return self._scalar("version")
    def status_id(self):
        return self._scalar("status", relation_id=True)

    def status(self):
        return self._relation("status", OrderStatusExpression)
    def customer_id(self):
        return self._scalar("customer", relation_id=True)

    def customer(self):
        return self._relation("customer", CustomerExpression)
    def commerce_platform_id(self):
        return self._scalar("commercePlatform", relation_id=True)

    def commerce_platform(self):
        return self._relation("commercePlatform", CommercePlatformExpression)
    def order_line_list(self):
        path = self._path_for("order_line_list")
        if self._error is not None:
            return ListExpression([], self._root, path, OrderLineExpression, self._error)
        if self._value is None:
            return ListExpression([], self._root, path, OrderLineExpression)
        if "order_line_list" not in getattr(self._value, "_loaded_fields", set()):
            return ListExpression([], self._root, path, OrderLineExpression, self._not_loaded("order_line_list"))
        return ListExpression(getattr(self._value, "_order_line_list"), self._root, path, OrderLineExpression)
    pass

class ProductExpression(EntityExpression):
    def id(self):
        return self._scalar("id")
    def name(self):
        return self._scalar("name")
    def sku(self):
        return self._scalar("sku")
    def image_url(self):
        return self._scalar("imageUrl")
    def create_time(self):
        return self._scalar("createTime")
    def update_time(self):
        return self._scalar("updateTime")
    def version(self):
        return self._scalar("version")
    def commerce_platform_id(self):
        return self._scalar("commercePlatform", relation_id=True)

    def commerce_platform(self):
        return self._relation("commercePlatform", CommercePlatformExpression)
    def order_line_list(self):
        path = self._path_for("order_line_list")
        if self._error is not None:
            return ListExpression([], self._root, path, OrderLineExpression, self._error)
        if self._value is None:
            return ListExpression([], self._root, path, OrderLineExpression)
        if "order_line_list" not in getattr(self._value, "_loaded_fields", set()):
            return ListExpression([], self._root, path, OrderLineExpression, self._not_loaded("order_line_list"))
        return ListExpression(getattr(self._value, "_order_line_list"), self._root, path, OrderLineExpression)
    pass

class OrderLineExpression(EntityExpression):
    def id(self):
        return self._scalar("id")
    def product_name(self):
        return self._scalar("productName")
    def sku(self):
        return self._scalar("sku")
    def quantity(self):
        return self._scalar("quantity")
    def create_time(self):
        return self._scalar("createTime")
    def version(self):
        return self._scalar("version")
    def customer_order_id(self):
        return self._scalar("customerOrder", relation_id=True)

    def customer_order(self):
        return self._relation("customerOrder", CustomerOrderExpression)
    def product_id(self):
        return self._scalar("product", relation_id=True)

    def product(self):
        return self._relation("product", ProductExpression)
    def commerce_platform_id(self):
        return self._scalar("commercePlatform", relation_id=True)

    def commerce_platform(self):
        return self._relation("commercePlatform", CommercePlatformExpression)
    pass

class OrderSearchPresetExpression(EntityExpression):
    def id(self):
        return self._scalar("id")
    def name(self):
        return self._scalar("name")
    def filter_json(self):
        return self._scalar("filterJson")
    def request_id(self):
        return self._scalar("requestId")
    def owner_user_id(self):
        return self._scalar("ownerUserId")
    def create_time(self):
        return self._scalar("createTime")
    def update_time(self):
        return self._scalar("updateTime")
    def version(self):
        return self._scalar("version")
    def commerce_platform_id(self):
        return self._scalar("commercePlatform", relation_id=True)

    def commerce_platform(self):
        return self._relation("commercePlatform", CommercePlatformExpression)
    pass

class E:
    @staticmethod
    def commerce_platform(value):
        entity_id = getattr(value, "id", None)
        return CommercePlatformExpression(value, "CommercePlatform(id={})".format(entity_id))
    @staticmethod
    def customer(value):
        entity_id = getattr(value, "id", None)
        return CustomerExpression(value, "Customer(id={})".format(entity_id))
    @staticmethod
    def order_status(value):
        entity_id = getattr(value, "id", None)
        return OrderStatusExpression(value, "OrderStatus(id={})".format(entity_id))
    @staticmethod
    def customer_order(value):
        entity_id = getattr(value, "id", None)
        return CustomerOrderExpression(value, "CustomerOrder(id={})".format(entity_id))
    @staticmethod
    def product(value):
        entity_id = getattr(value, "id", None)
        return ProductExpression(value, "Product(id={})".format(entity_id))
    @staticmethod
    def order_line(value):
        entity_id = getattr(value, "id", None)
        return OrderLineExpression(value, "OrderLine(id={})".format(entity_id))
    @staticmethod
    def order_search_preset(value):
        entity_id = getattr(value, "id", None)
        return OrderSearchPresetExpression(value, "OrderSearchPreset(id={})".format(entity_id))
    pass