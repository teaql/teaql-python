"""#236: actual generated Q/E/save, empty aggregates and SQLite failure lineage.

Pass an evaluated generated scalar library as the sole argument. No generated
implementation is inspected or edited. Fault injection changes only this
test-owned provider descriptor; the failed query still reaches real SQLite.
"""
import asyncio
from copy import deepcopy
from dataclasses import fields, is_dataclass
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
import json
import os
from pathlib import Path
import sqlite3
import sys
from uuid import uuid4

assert len(sys.argv) <= 2
sys.path.insert(0, str((Path(sys.argv[1]) if len(sys.argv) == 2
                      else Path(__file__).with_name("generated")).resolve()))
from E import E
from Q import Q
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.core.value import Value
from teaql.provider.sqlite import create_sqlite_service
from teaql.runtime import UserContext
from teaql.sql.executor import TransportError
from main import new_probe

PURPOSE = "verify generated empty aggregate contract"


def plain(value):
    if isinstance(value, Value):
        return plain(value.val)
    if isinstance(value, Enum):
        return value.name
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime, time)):
        return value.isoformat()
    if is_dataclass(value):
        return {item.name: plain(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(item) for item in value]
    return value


class Telemetry:
    """A local diagnostic sink, no exporter or background service."""
    def __init__(self):
        self.rows = []

    def start(self, operation):
        class Scope:
            correlation = (uuid4().int, uuid4().int >> 64)

            def success(self, attributes=None):
                pass

            def failure(self, error):
                pass
        return Scope()

    def record_diagnostic(self, attributes, correlation):
        self.rows.append({"attributes": dict(attributes),
                          "correlation": [f"{correlation[0]:032x}", f"{correlation[1]:016x}"]})


async def main():
    round_number = int(os.environ["TEAQL_EMPTY_ROUND"])
    database = Path(os.environ["TEAQL_EMPTY_DB"])
    assert database.exists() == (round_number == 2), "do not reset a repeated run"
    vectors = json.loads(Path(os.environ.get("TEAQL_EMPTY_VECTORS",
                               Path(__file__).with_name("empty-aggregate-vectors.json"))).read_text())
    service = create_sqlite_service(str(database))
    telemetry = Telemetry()
    context = (UserContext().install(GENERATED_RUNTIME_MODULE)
               .insert_resource("dataService", service).with_runtime_telemetry(telemetry))
    context.set_diagnostic_sql_log_sink(None)
    report = {"schema": "teaql.python-generated-empty-aggregate/v1", "round": round_number,
              "passed": False, "rows": [], "requestSnapshots": [], "serializationGaps": []}
    driver, metadata = [], []
    original_fetch = service.transport.fetch_all_sql
    original_metadata = context._record_metadata_log

    async def capture(compiled):
        fact = {"sql": compiled.sql, "commentedSQL": compiled.sql_with_comment()}
        driver.append(fact)
        try:
            result = await original_fetch(compiled)
            fact.update(rows=len(result), outcome="success")
            return result
        except sqlite3.Error as error:
            # sqlite_errorcode was added in Python 3.11. Preserve its actual
            # absence on supported Python 3.10; never fabricate native code 1.
            fact.update(outcome="failure", sqliteCode=getattr(error, "sqlite_errorcode", None),
                        sqliteError=type(error).__name__)
            raise

    def capture_metadata(record, *args, **kwargs):
        metadata.append(deepcopy(record))
        return original_metadata(record, *args, **kwargs)

    async def execute(request, case, logging, *, typed=False, fail=False):
        request.comment("inspect " + case)
        executable = request.purpose(PURPOSE)
        before = {"query": plain(deepcopy(request.query)),
                  "comment": request._comment, "purpose": request._purpose}
        driver.clear()
        metadata.clear()
        telemetry.rows.clear()
        context.clear_sql_logs()
        result = None
        try:
            result = await (executable.execute_for_list(context) if typed
                            else executable.execute_for_result(context))
            assert not fail, "the nonexistent table unexpectedly existed"
        except TransportError as error:
            assert fail and isinstance(error.error, sqlite3.OperationalError)
            assert getattr(error.error, "sqlite_errorcode", None) in (None, 1)
        after = {"query": plain(request.query),
                 "comment": request._comment, "purpose": request._purpose}
        assert before == after, "execution mutated the caller's query"
        report["requestSnapshots"].append({"before": before, "after": after})
        assert len(driver) == len(metadata) == len(telemetry.rows), (
            len(driver), len(metadata), len(telemetry.rows))
        facts = []
        for raw, entry, diagnostic in zip(driver, metadata, telemetry.rows):
            assert raw["sql"] == entry.parameterized_sql
            assert raw["outcome"] == entry.execution_outcome
            assert entry.purpose == PURPOSE and entry.comment
            attrs = diagnostic["attributes"]
            assert attrs["teaql.sql.outcome"] == raw["outcome"]
            assert attrs["teaql.sql.log_mode"] == "masked"
            if raw["outcome"] == "success":
                assert attrs["teaql.sql.result_count"] == raw["rows"]
            else:
                assert "teaql.sql.result_count" not in attrs
                assert raw["sqliteError"] == "OperationalError" and raw["sqliteCode"] in (None, 1)
            facts.append({**raw, "comment": entry.comment, "purpose": entry.purpose,
                          "traceChain": plain(entry.request_trace_chain),
                          "tracePath": plain(entry.trace_chain), "diagnostic": diagnostic})
        assert len(context.sql_logs()) == (len(facts) if logging else 0)
        observed = {"case": case, "logging": logging, "sql": facts}
        if not typed and result is not None:
            assert result.metadata.backend == "sqlite"
            observed["responseMetadata"] = {
                "backend": result.metadata.backend,
                "operation": result.metadata.operation.name,
                "outcome": result.metadata.execution_outcome,
                "resultCount": result.metadata.result_count,
            }
        report["rows"].append(observed)
        return result, observed

    async def seed(label, values):
        parent = (Q.type_platforms().comment("initialize aggregate bucket")
                  .purpose("prepare deterministic empty aggregate input")
                  .new_entity(context).update_name(label))
        await parent.audit_as("create aggregate bucket through generated mutation").save(context)
        for value in values:
            child = (new_probe(context, label, Decimal("1.00"))
                     .update_type_platform(parent).update_optional_integer(value))
            await child.audit_as("create aggregate contribution through generated mutation").save(context)
        return E.type_platform(parent).id().eval()

    def scalar_request(parent):
        return Q.scalar_type_probes_minimal().filter_by_type_platform(parent).limit(10)

    try:
        await context.ensure_schema()
        report["scalarIds"] = [
            await seed(f"EA236-{round_number}-scalar-{vector['id']}", vector["values"])
            for vector in vectors["scalarCases"]]
        bucket_values = vectors["bucketCases"][1]
        report["bucketIds"] = [
            await seed(f"EA236-{round_number}-bucket-{parent}",
                       [child["value"] for child in bucket_values["children"]
                        if child["parent"] == parent])
            for parent in range(1, 5)]
        service.transport.fetch_all_sql = capture
        context._record_metadata_log = capture_metadata
        for logging in (True, False):
            context.enable_all_sql_log() if logging else context.disable_sql_log()
            for parent, vector in zip(report["scalarIds"], vectors["scalarCases"]):
                request = scalar_request(parent).sum_optional_integer_as("total").count_as("rows")
                result, row = await execute(request, vector["id"], logging)
                assert len(result.rows) == 1 and "total" in result.rows[0]
                row["values"] = plain(result.rows[0])
                assert row["values"]["total"] == vector["sum"]
                assert row["values"]["rows"] == vector["countStar"]
                known, counted = await execute(
                    scalar_request(parent).with_optional_integer_is_known().count_as("values"),
                    vector["id"] + "-COUNT-VALUE", logging)
                assert known.rows[0]["values"] == vector["countValue"]
                counted["values"] = plain(known.rows[0])
                assert json.loads(json.dumps(row["values"]))["total"] == vector["sum"]
            request = (Q.type_platforms().with_id_is(report["bucketIds"][3]).limit(1)
                       .count_scalar_type_probes_with(
                           "rows", Q.scalar_type_probes().limit(10).comment("count aggregate contributions"))
                       .sum_optional_integer_of_scalar_type_probes_as(
                           "total", Q.scalar_type_probes().limit(10).comment("sum aggregate contributions")))
            result, row = await execute(request, "EA-05", logging, typed=True)
            assert len(result) == 1
            entity = result[0]
            assert E.type_platform(entity).id().eval() == report["bucketIds"][3]
            assert entity.get_dynamic_property("rows") == 0
            assert entity.get_dynamic_property("total") is None
            row["entityJSON"] = json.loads(entity.to_json())
            row["values"] = {"rows": entity.get_dynamic_property("rows"),
                             "total": entity.get_dynamic_property("total")}
            for alias in ("rows", "total"):
                if alias not in row["entityJSON"]:
                    report["serializationGaps"].append({"case": "EA-05", "logging": logging,
                                                       "alias": alias, "reason": "selected alias omitted"})
                else:
                    assert row["entityJSON"][alias] == row["values"][alias]
                    assert type(row["entityJSON"][alias]) is type(row["values"][alias])
            for include_all in (True, False):
                choices = (Q.type_platforms().with_name_starting_with(f"EA236-{round_number}-bucket-")
                           .order_by_id_ascending().limit(10).count_as("rows")
                           .sum_optional_integer_of_scalar_type_probes_as(
                               "total", Q.scalar_type_probes().limit(10).comment("sum facet contributions")))
                request = (Q.scalar_type_probes().with_required_string_starting_with(
                    f"EA236-{round_number}-bucket-").limit(1)
                    .facet_by_type_platform_as("buckets", choices, include_all))
                result, row = await execute(request, "EA-06", logging)
                row["includeAll"] = include_all
                row["visibleRows"] = len(result.rows)
                facet = result.facets["buckets"]
                row["values"] = [{"parent": report["bucketIds"].index(item["id"]) + 1,
                                  "count": item["rows"], "sum": item["total"]} for item in facet]
                expected = bucket_values["expected"]
                assert row["visibleRows"] == 1
                assert row["values"] == (expected if include_all else [v for v in expected if v["count"]])
            raw, row = await execute(
                scalar_request(report["scalarIds"][0]).sum_optional_integer_as("total"), "EA-07", logging)
            value = raw.rows[0]["total"]
            row["values"] = {"raw": value, "fallback": value if value is not None else 0,
                             "rawRemains": raw.rows[0]["total"]}
            assert row["values"] == {"raw": None, "fallback": 0, "rawRemains": None}
            result, row = await execute(
                scalar_request(report["scalarIds"][0]).group_by_required_integer()
                .sum_optional_integer_as("total"), "EA-08", logging)
            row["groups"] = plain(result.rows)
            assert row["groups"] == []
            descriptor = service.schema_provider.get_entity("ScalarTypeProbe")
            original_table = descriptor.table_name_val
            try:
                descriptor.table_name_val = "ea236_fault_scalar_data"
                _, row = await execute(scalar_request(report["scalarIds"][0])
                                       .sum_optional_integer_as("total"), "REAL-SQLITE-FAILURE",
                                       logging, fail=True)
                assert len(row["sql"]) == 1 and row["sql"][0]["sqliteCode"] in (None, 1)
            finally:
                descriptor.table_name_val = original_table
            result, row = await execute(Q.type_platforms().with_id_is(report["bucketIds"][3])
                                        .limit(1), "QUERY-RECOVERY", logging)
            assert len(result.rows) == 1
            assert len(row["sql"][0]["traceChain"]) == 2
        report["passed"] = not report["serializationGaps"]
        assert report["passed"], "selected aggregate aliases were lost at the entity JSON boundary"
    finally:
        await service.close()
        print("PYTHON_GENERATED_EMPTY_AGGREGATE=" + json.dumps(report, default=plain, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())
