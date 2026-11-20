from teaql.runtime import ExpressionPath, JsonFieldNamingProfile, TeaQLNotLoadedError


class ValueExpression:
    def __init__(self, value=None, error=None):
        self._value = value
        self._error = error

    def eval(self):
        if self._error is not None:
            raise self._error.terminal("eval()")
        return self._value

    def or_if_null(self, fallback):
        if self._error is not None:
            raise self._error.terminal("or_if_null(<fallback>)")
        return fallback if self._value is None else self._value


class EntityExpression:
    def __init__(self, value, root=None, path=None, error=None):
        self._value = value
        self._root = root
        self._path = path if path is not None else ExpressionPath("E.entity(<root>)")
        self._error = error

    def eval(self):
        if self._error is not None:
            raise self._error.terminal("eval()")
        return self._value

    def _scalar(self, field, canonical, method, relation_id=False):
        path = self._path.member(canonical, method)
        if self._error is not None:
            return ValueExpression(error=self._error.with_path(path))
        if self._value is None:
            return ValueExpression(None)
        if field not in getattr(self._value, "_loaded_fields", set()):
            return ValueExpression(error=TeaQLNotLoadedError(path.mark_missing(), canonical))
        value = getattr(self._value, field)
        if relation_id and value is not None and not isinstance(value, (int, str)):
            value = getattr(value, "id", None)
        return ValueExpression(value)

    def _relation(self, field, canonical, method, expression_type):
        path = self._path.member(canonical, method)
        if self._error is not None:
            return expression_type(None, self._root, path, self._error.with_path(path))
        if self._value is None:
            return expression_type(None, self._root, path)
        if field not in getattr(self._value, "_loaded_fields", set()):
            return expression_type(None, self._root, path, TeaQLNotLoadedError(path.mark_missing(), canonical))
        value = getattr(self._value, field)
        if value is not None and isinstance(value, (int, str)):
            return expression_type(None, self._root, path, TeaQLNotLoadedError(path.mark_missing(), canonical))
        return expression_type(value, self._root, path)

    def _list(self, field, canonical, method, item_expression):
        path = self._path.member(canonical, method)
        if self._error is not None:
            return ListExpression([], self._root, path, item_expression, self._error.with_path(path))
        if self._value is None:
            return ListExpression([], self._root, path, item_expression)
        if field not in getattr(self._value, "_loaded_fields", set()):
            return ListExpression([], self._root, path, item_expression, TeaQLNotLoadedError(path.mark_missing(), canonical))
        return ListExpression(getattr(self._value, "_" + field), self._root, path, item_expression)


class ListExpression:
    def __init__(self, values, root, path, item_expression, error=None):
        self._values = values
        self._root = root
        self._path = path
        self._item_expression = item_expression
        self._error = error

    def size(self):
        return (ValueExpression(error=self._error.with_path(self._path.operation("size()")))
                if self._error else ValueExpression(len(self._values)))

    def first(self):
        return self._item(0, first=True)

    def get(self, index):
        return self._item(index)

    def _item(self, index, first=False):
        path = self._path.index(index, first)
        if self._error is not None:
            return self._item_expression(None, self._root, path, self._error.with_path(path))
        value = self._values[index] if 0 <= index < len(self._values) else None
        return self._item_expression(value, self._root, path)


class CommercePlatformExpression(EntityExpression):
    def id(self):
        return self._scalar("id", "id", "id")
    def name(self):
        return self._scalar("name", "name", "name")
    def version(self):
        return self._scalar("version", "version", "version")
    def customer_order_list(self):
        return self._list("customer_order_list", "customer_order_list", "customer_order_list", CustomerOrderExpression)
    pass

class CustomerOrderExpression(EntityExpression):
    def id(self):
        return self._scalar("id", "id", "id")
    def order_number(self):
        return self._scalar("orderNumber", "order_number", "order_number")
    def version(self):
        return self._scalar("version", "version", "version")
    def commerce_platform_id(self):
        return self._scalar("commercePlatform", "commerce_platform", "commerce_platform_id", relation_id=True)

    def commerce_platform(self):
        return self._relation("commercePlatform", "commerce_platform", "commerce_platform", CommercePlatformExpression)
    def order_attachment_list(self):
        return self._list("order_attachment_list", "order_attachment_list", "order_attachment_list", OrderAttachmentExpression)
    pass

class OrderAttachmentExpression(EntityExpression):
    def id(self):
        return self._scalar("id", "id", "id")
    def file_name(self):
        return self._scalar("fileName", "file_name", "file_name")
    def content_type(self):
        return self._scalar("contentType", "content_type", "content_type")
    def content_length(self):
        return self._scalar("contentLength", "content_length", "content_length")
    def content_sha256(self):
        return self._scalar("contentSha256", "content_sha256", "content_sha256")
    def object_key(self):
        return self._scalar("objectKey", "object_key", "object_key")
    def version(self):
        return self._scalar("version", "version", "version")
    def customer_order_id(self):
        return self._scalar("customerOrder", "customer_order", "customer_order_id", relation_id=True)

    def customer_order(self):
        return self._relation("customerOrder", "customer_order", "customer_order", CustomerOrderExpression)
    pass

class E:
    @staticmethod
    def commerce_platform(value):
        return CommercePlatformExpression(value, path=ExpressionPath(
            "E.commerce_platform(<root>)", JsonFieldNamingProfile.parse("camelCase")))
    @staticmethod
    def customer_order(value):
        return CustomerOrderExpression(value, path=ExpressionPath(
            "E.customer_order(<root>)", JsonFieldNamingProfile.parse("camelCase")))
    @staticmethod
    def order_attachment(value):
        return OrderAttachmentExpression(value, path=ExpressionPath(
            "E.order_attachment(<root>)", JsonFieldNamingProfile.parse("camelCase")))
    pass