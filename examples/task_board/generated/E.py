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
    def founded(self):
        return self._scalar("founded")
    def user_email(self):
        return self._scalar("userEmail")
    def version(self):
        return self._scalar("version")
    def task_status_list(self):
        path = self._path_for("task_status_list")
        if self._error is not None:
            return ListExpression([], self._root, path, TaskStatusExpression, self._error)
        if self._value is None:
            return ListExpression([], self._root, path, TaskStatusExpression)
        if "task_status_list" not in getattr(self._value, "_loaded_fields", set()):
            return ListExpression([], self._root, path, TaskStatusExpression, self._not_loaded("task_status_list"))
        return ListExpression(getattr(self._value, "_task_status_list"), self._root, path, TaskStatusExpression)
    def task_list(self):
        path = self._path_for("task_list")
        if self._error is not None:
            return ListExpression([], self._root, path, TaskExpression, self._error)
        if self._value is None:
            return ListExpression([], self._root, path, TaskExpression)
        if "task_list" not in getattr(self._value, "_loaded_fields", set()):
            return ListExpression([], self._root, path, TaskExpression, self._not_loaded("task_list"))
        return ListExpression(getattr(self._value, "_task_list"), self._root, path, TaskExpression)
    pass

class TaskStatusExpression(EntityExpression):
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
    def progress(self):
        return self._scalar("progress")
    def version(self):
        return self._scalar("version")
    def platform_id(self):
        return self._scalar("platform", relation_id=True)

    def platform(self):
        return self._relation("platform", PlatformExpression)
    def task_list(self):
        path = self._path_for("task_list")
        if self._error is not None:
            return ListExpression([], self._root, path, TaskExpression, self._error)
        if self._value is None:
            return ListExpression([], self._root, path, TaskExpression)
        if "task_list" not in getattr(self._value, "_loaded_fields", set()):
            return ListExpression([], self._root, path, TaskExpression, self._not_loaded("task_list"))
        return ListExpression(getattr(self._value, "_task_list"), self._root, path, TaskExpression)
    pass

class TaskExpression(EntityExpression):
    def id(self):
        return self._scalar("id")
    def name(self):
        return self._scalar("name")
    def version(self):
        return self._scalar("version")
    def status_id(self):
        return self._scalar("status", relation_id=True)

    def status(self):
        return self._relation("status", TaskStatusExpression)
    def platform_id(self):
        return self._scalar("platform", relation_id=True)

    def platform(self):
        return self._relation("platform", PlatformExpression)
    def task_execution_log_list(self):
        path = self._path_for("task_execution_log_list")
        if self._error is not None:
            return ListExpression([], self._root, path, TaskExecutionLogExpression, self._error)
        if self._value is None:
            return ListExpression([], self._root, path, TaskExecutionLogExpression)
        if "task_execution_log_list" not in getattr(self._value, "_loaded_fields", set()):
            return ListExpression([], self._root, path, TaskExecutionLogExpression, self._not_loaded("task_execution_log_list"))
        return ListExpression(getattr(self._value, "_task_execution_log_list"), self._root, path, TaskExecutionLogExpression)
    pass

class TaskExecutionLogExpression(EntityExpression):
    def id(self):
        return self._scalar("id")
    def action(self):
        return self._scalar("action")
    def detail(self):
        return self._scalar("detail")
    def version(self):
        return self._scalar("version")
    def task_id(self):
        return self._scalar("task", relation_id=True)

    def task(self):
        return self._relation("task", TaskExpression)
    pass

class E:
    @staticmethod
    def platform(value):
        entity_id = getattr(value, "id", None)
        return PlatformExpression(value, "Platform(id={})".format(entity_id))
    @staticmethod
    def task_status(value):
        entity_id = getattr(value, "id", None)
        return TaskStatusExpression(value, "TaskStatus(id={})".format(entity_id))
    @staticmethod
    def task(value):
        entity_id = getattr(value, "id", None)
        return TaskExpression(value, "Task(id={})".format(entity_id))
    @staticmethod
    def task_execution_log(value):
        entity_id = getattr(value, "id", None)
        return TaskExecutionLogExpression(value, "TaskExecutionLog(id={})".format(entity_id))
    pass