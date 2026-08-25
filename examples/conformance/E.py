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
    def work_item_list(self):
        path = self._path_for("work_item_list")
        if self._error is not None:
            return ListExpression([], self._root, path, WorkItemExpression, self._error)
        if self._value is None:
            return ListExpression([], self._root, path, WorkItemExpression)
        if "work_item_list" not in getattr(self._value, "_loaded_fields", set()):
            return ListExpression([], self._root, path, WorkItemExpression, self._not_loaded("work_item_list"))
        return ListExpression(getattr(self._value, "_work_item_list"), self._root, path, WorkItemExpression)
    pass

class WorkItemExpression(EntityExpression):
    def id(self):
        return self._scalar("id")
    def title(self):
        return self._scalar("title")
    def description(self):
        return self._scalar("description")
    def version(self):
        return self._scalar("version")
    def platform_id(self):
        return self._scalar("platform", relation_id=True)

    def platform(self):
        return self._relation("platform", PlatformExpression)
    pass

class E:
    @staticmethod
    def platform(value):
        entity_id = getattr(value, "id", None)
        return PlatformExpression(value, "Platform(id={})".format(entity_id))
    @staticmethod
    def work_item(value):
        entity_id = getattr(value, "id", None)
        return WorkItemExpression(value, "WorkItem(id={})".format(entity_id))
    pass