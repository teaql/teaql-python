from teaql.runtime import CheckResult, RuntimeModule
from teaql.core.value import Value
from models.platform import Platform
from models.work_item import WorkItem

def _teaql_is_null(value):
    return value.is_null() if hasattr(value, "is_null") else value is None

def _teaql_raw(value):
    return value.val if hasattr(value, "val") else value

def _teaql_entity_id(value):
    value = _teaql_raw(value)
    if hasattr(value, "id"):
        return value.id
    if isinstance(value, dict):
        return value.get("id")
    return value

class _PlatformChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        now = context.get_resource("fix_time")
        if (operation == "insert" and "name" not in record) or ("name" in record and _teaql_is_null(record["name"])):
            results.append(CheckResult("required", "name"))
        if "name" in record and _teaql_raw(record["name"]) is not None and len(_teaql_raw(record["name"])) > 100:
            results.append(CheckResult("max_length", "name", _teaql_raw(record["name"]), 100))



class _WorkItemChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        now = context.get_resource("fix_time")
        if (operation == "insert" and "title" not in record) or ("title" in record and _teaql_is_null(record["title"])):
            results.append(CheckResult("required", "title"))
        if "title" in record and _teaql_raw(record["title"]) is not None and not len(_teaql_raw(record["title"])) >= 1:
            results.append(CheckResult("min_length", "title", _teaql_raw(record["title"]), 1))
        if "title" in record and _teaql_raw(record["title"]) is not None and len(_teaql_raw(record["title"])) > 80:
            results.append(CheckResult("max_length", "title", _teaql_raw(record["title"]), 80))

        if "description" in record and _teaql_raw(record["description"]) is not None and len(_teaql_raw(record["description"])) > 100:
            results.append(CheckResult("max_length", "description", _teaql_raw(record["description"]), 100))

        if (operation == "insert" and "platform" not in record) or ("platform" in record and _teaql_is_null(record["platform"])):
            results.append(CheckResult("required", "platform"))



# Passive generated manifest. Call ensure_schema() separately and explicitly.
GENERATED_RUNTIME_MODULE = (RuntimeModule().entity(Platform)
    .checker("Platform", _PlatformChecker()).entity(WorkItem)
    .checker("WorkItem", _WorkItemChecker())
)