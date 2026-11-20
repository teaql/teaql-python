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


class PlatformExpression(EntityExpression):
    def id(self):
        return self._scalar("id", "id", "id")
    def name(self):
        return self._scalar("name", "name", "name")
    def founded(self):
        return self._scalar("founded", "founded", "founded")
    def user_email(self):
        return self._scalar("userEmail", "user_email", "user_email")
    def version(self):
        return self._scalar("version", "version", "version")
    def task_status_list(self):
        return self._list("task_status_list", "task_status_list", "task_status_list", TaskStatusExpression)
    def task_list(self):
        return self._list("task_list", "task_list", "task_list", TaskExpression)
    pass

class TaskStatusExpression(EntityExpression):
    def id(self):
        return self._scalar("id", "id", "id")
    def name(self):
        return self._scalar("name", "name", "name")
    def code(self):
        return self._scalar("code", "code", "code")
    def color(self):
        return self._scalar("color", "color", "color")
    def display_order(self):
        return self._scalar("displayOrder", "display_order", "display_order")
    def progress(self):
        return self._scalar("progress", "progress", "progress")
    def version(self):
        return self._scalar("version", "version", "version")
    def platform_id(self):
        return self._scalar("platform", "platform", "platform_id", relation_id=True)

    def platform(self):
        return self._relation("platform", "platform", "platform", PlatformExpression)
    def task_list(self):
        return self._list("task_list", "task_list", "task_list", TaskExpression)
    pass

class TaskExpression(EntityExpression):
    def id(self):
        return self._scalar("id", "id", "id")
    def name(self):
        return self._scalar("name", "name", "name")
    def version(self):
        return self._scalar("version", "version", "version")
    def status_id(self):
        return self._scalar("status", "status", "status_id", relation_id=True)

    def status(self):
        return self._relation("status", "status", "status", TaskStatusExpression)
    def platform_id(self):
        return self._scalar("platform", "platform", "platform_id", relation_id=True)

    def platform(self):
        return self._relation("platform", "platform", "platform", PlatformExpression)
    def task_execution_log_list(self):
        return self._list("task_execution_log_list", "task_execution_log_list", "task_execution_log_list", TaskExecutionLogExpression)
    pass

class TaskExecutionLogExpression(EntityExpression):
    def id(self):
        return self._scalar("id", "id", "id")
    def action(self):
        return self._scalar("action", "action", "action")
    def detail(self):
        return self._scalar("detail", "detail", "detail")
    def version(self):
        return self._scalar("version", "version", "version")
    def task_id(self):
        return self._scalar("task", "task", "task_id", relation_id=True)

    def task(self):
        return self._relation("task", "task", "task", TaskExpression)
    pass

class E:
    @staticmethod
    def platform(value):
        return PlatformExpression(value, path=ExpressionPath(
            "E.platform(<root>)", JsonFieldNamingProfile.parse("camelCase")))
    @staticmethod
    def task_status(value):
        return TaskStatusExpression(value, path=ExpressionPath(
            "E.task_status(<root>)", JsonFieldNamingProfile.parse("camelCase")))
    @staticmethod
    def task(value):
        return TaskExpression(value, path=ExpressionPath(
            "E.task(<root>)", JsonFieldNamingProfile.parse("camelCase")))
    @staticmethod
    def task_execution_log(value):
        return TaskExecutionLogExpression(value, path=ExpressionPath(
            "E.task_execution_log(<root>)", JsonFieldNamingProfile.parse("camelCase")))
    pass