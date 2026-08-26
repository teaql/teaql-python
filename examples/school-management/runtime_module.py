from datetime import datetime, timezone
from teaql.runtime import CheckResult, RuntimeModule
from teaql.core.value import Value
try:
    from teaql.core.graph import GraphNode
except ImportError:
    class GraphNode:
        def __init__(self, entity):
            self.entity, self.fields = entity, {}
        def set(self, field, value):
            self.fields[field] = value
            return self
from models.platform import Platform
from models.school_type import SchoolType
from models.school import School

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
        if operation == "insert" and ("create_time" not in record or _teaql_is_null(record["create_time"])):
            record["create_time"] = Value.from_any(now)

        if operation == "insert" and ("update_time" not in record or _teaql_is_null(record["update_time"])):
            record["update_time"] = Value.from_any(now)
        if operation == "update":
            record["update_time"] = Value.from_any(now)


        if (operation == "insert" and "name" not in record) or ("name" in record and _teaql_is_null(record["name"])):
            results.append(CheckResult("required", "name"))
        if "name" in record and _teaql_raw(record["name"]) is not None and len(_teaql_raw(record["name"])) > 100:
            results.append(CheckResult("max_length", "name", _teaql_raw(record["name"]), 100))

        if (operation == "insert" and "base_url" not in record) or ("base_url" in record and _teaql_is_null(record["base_url"])):
            results.append(CheckResult("required", "baseUrl"))
        if "base_url" in record and _teaql_raw(record["base_url"]) is not None and len(_teaql_raw(record["base_url"])) > 100:
            results.append(CheckResult("max_length", "baseUrl", _teaql_raw(record["base_url"]), 100))

        if (operation == "insert" and "create_time" not in record) or ("create_time" in record and _teaql_is_null(record["create_time"])):
            results.append(CheckResult("required", "createTime"))

        if (operation == "insert" and "update_time" not in record) or ("update_time" in record and _teaql_is_null(record["update_time"])):
            results.append(CheckResult("required", "updateTime"))



class _SchoolTypeChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        now = context.get_resource("fix_time")
        if (operation == "insert" and "platform" not in record) or ("platform" in record and _teaql_is_null(record["platform"])):
            results.append(CheckResult("required", "platform"))


        if (operation == "insert" and "name" not in record) or ("name" in record and _teaql_is_null(record["name"])):
            results.append(CheckResult("required", "name"))
        if "name" in record and _teaql_raw(record["name"]) is not None and len(_teaql_raw(record["name"])) > 100:
            results.append(CheckResult("max_length", "name", _teaql_raw(record["name"]), 100))

        if (operation == "insert" and "code" not in record) or ("code" in record and _teaql_is_null(record["code"])):
            results.append(CheckResult("required", "code"))
        if "code" in record and _teaql_raw(record["code"]) is not None and len(_teaql_raw(record["code"])) > 100:
            results.append(CheckResult("max_length", "code", _teaql_raw(record["code"]), 100))

        if (operation == "insert" and "display_order" not in record) or ("display_order" in record and _teaql_is_null(record["display_order"])):
            results.append(CheckResult("required", "displayOrder"))



class _SchoolChecker:
    def check_and_fix(self, context, record, location, results):
        operation = context.get_resource("fix_operation")
        now = context.get_resource("fix_time")
        if operation == "insert" and ("create_time" not in record or _teaql_is_null(record["create_time"])):
            record["create_time"] = Value.from_any(now)

        if operation == "insert" and ("update_time" not in record or _teaql_is_null(record["update_time"])):
            record["update_time"] = Value.from_any(now)
        if operation == "update":
            record["update_time"] = Value.from_any(now)


        if (operation == "insert" and "platform" not in record) or ("platform" in record and _teaql_is_null(record["platform"])):
            results.append(CheckResult("required", "platform"))

        if (operation == "insert" and "school_type" not in record) or ("school_type" in record and _teaql_is_null(record["school_type"])):
            results.append(CheckResult("required", "schoolType"))

        if (operation == "insert" and "name" not in record) or ("name" in record and _teaql_is_null(record["name"])):
            results.append(CheckResult("required", "name"))
        if "name" in record and _teaql_raw(record["name"]) is not None and len(_teaql_raw(record["name"])) > 100:
            results.append(CheckResult("max_length", "name", _teaql_raw(record["name"]), 100))

        if (operation == "insert" and "address" not in record) or ("address" in record and _teaql_is_null(record["address"])):
            results.append(CheckResult("required", "address"))
        if "address" in record and _teaql_raw(record["address"]) is not None and len(_teaql_raw(record["address"])) > 100:
            results.append(CheckResult("max_length", "address", _teaql_raw(record["address"]), 100))

        if (operation == "insert" and "established_date" not in record) or ("established_date" in record and _teaql_is_null(record["established_date"])):
            results.append(CheckResult("required", "establishedDate"))

        if (operation == "insert" and "student_capacity" not in record) or ("student_capacity" in record and _teaql_is_null(record["student_capacity"])):
            results.append(CheckResult("required", "studentCapacity"))

        if (operation == "insert" and "active" not in record) or ("active" in record and _teaql_is_null(record["active"])):
            results.append(CheckResult("required", "active"))

        if (operation == "insert" and "create_time" not in record) or ("create_time" in record and _teaql_is_null(record["create_time"])):
            results.append(CheckResult("required", "createTime"))

        if (operation == "insert" and "update_time" not in record) or ("update_time" in record and _teaql_is_null(record["update_time"])):
            results.append(CheckResult("required", "updateTime"))



# Passive generated manifest. Call ensure_schema() separately and explicitly.
GENERATED_RUNTIME_MODULE = (RuntimeModule().entity(Platform)
    .checker("Platform", _PlatformChecker()).entity(SchoolType)
    .checker("SchoolType", _SchoolTypeChecker()).entity(School)
    .checker("School", _SchoolChecker())

    .root_graph(GraphNode("Platform").set("id", 1).set("name", "Campus Learning Platform").set("base_url", "https://campus.example.com").set("create_time", datetime.now(timezone.utc)).set("update_time", datetime.now(timezone.utc)))
    .initial_graph(GraphNode("SchoolType").set("id", 1001).set("platform", 1).set("name", "Primary").set("code", "PRIMARY").set("display_order", 1))
    .initial_graph(GraphNode("SchoolType").set("id", 1002).set("platform", 1).set("name", "Secondary").set("code", "SECONDARY").set("display_order", 2))
)