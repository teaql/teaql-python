"""Generated entity JSON: exact values, projections, relations and safe saves."""

import asyncio
from collections import Counter
from datetime import date, datetime, time, timezone
from decimal import Decimal
import json
import math
import os
from pathlib import Path
from uuid import uuid4

from E import E, TeaQLNotLoadedError
from Q import Q
from main import new_probe
from models.scalar_type_probe import ScalarTypeProbe
from models.type_platform import TypePlatform
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.data_service import SQLiteTeaQLClient
from teaql.runtime import CheckException, EntityJSONError, JsonFieldNamingProfile, UserContext


class ObservedService:
    """Count forbidden boundary calls without replacing the real SQLite service."""

    def __init__(self, service):
        self.service = service
        self.calls = Counter(query=0, mutate=0, begin=0, next_id=0)

    def __getattr__(self, name):
        return getattr(self.service, name)

    async def query(self, *args, **kwargs):
        self.calls["query"] += 1
        return await self.service.query(*args, **kwargs)

    async def mutate(self, *args, **kwargs):
        self.calls["mutate"] += 1
        return await self.service.mutate(*args, **kwargs)

    async def begin(self, *args, **kwargs):
        self.calls["begin"] += 1
        return await self.service.begin(*args, **kwargs)

    async def next_id(self, *args, **kwargs):
        self.calls["next_id"] += 1
        return await self.service.next_id(*args, **kwargs)


def scalar_values(row):
    """Only generated E accessors, including nullable values and managed fields."""
    expression = E.scalar_type_probe(row)
    return {
        "required_string": expression.required_string().eval(),
        "optional_string": expression.optional_string().eval(),
        "large_text": expression.large_text().eval(),
        "required_boolean": expression.required_boolean().eval(),
        "optional_boolean": expression.optional_boolean().eval(),
        "required_integer": expression.required_integer().eval(),
        "optional_integer": expression.optional_integer().eval(),
        "required_long": expression.required_long().eval(),
        "optional_long": expression.optional_long().eval(),
        "required_decimal": expression.required_decimal().eval(),
        "optional_decimal": expression.optional_decimal().eval(),
        "required_float": expression.required_float().eval(),
        "optional_float": expression.optional_float().eval(),
        "required_double": expression.required_double().eval(),
        "optional_double": expression.optional_double().eval(),
        "required_date": expression.required_date().eval(),
        "optional_date": expression.optional_date().eval(),
        "required_time": expression.required_time().eval(),
        "optional_time": expression.optional_time().eval(),
        "required_datetime": expression.required_datetime().eval(),
        "optional_datetime": expression.optional_datetime().eval(),
        "id": expression.id().eval(),
        "version": expression.version().eval(),
        "type_platform": expression.type_platform_id().eval(),
        "create_time": expression.create_time().eval(),
        "update_time": expression.update_time().eval(),
    }


async def main():
    client = SQLiteTeaQLClient(os.environ["TEAQL_SCALAR_PROBE_DB"])
    observed = ObservedService(client)
    context = UserContext().install(GENERATED_RUNTIME_MODULE).insert_resource("dataService", observed)
    checks = []

    def check(condition, name):
        assert condition, name
        checks.append(name)

    def not_loaded(operation, name):
        before = observed.calls.copy()
        try:
            operation()
        except TeaQLNotLoadedError:
            check(observed.calls == before, name)
        else:
            raise AssertionError(name + ": unselected data became loaded")

    async def load(identity):
        return await (Q.scalar_type_probes().with_id_is(identity).limit(1)
                      .comment("reload exact entity JSON fixture")
                      .purpose("verify the generated SQLite JSON contract").execute_for_one(context))

    marker = "entity-json-" + uuid4().hex
    try:
        await context.ensure_schema()
        original = new_probe(context, marker, Decimal("9007199254740993.123456789"))
        original.update_required_boolean(False)
        original.update_optional_string("")
        original.update_optional_boolean(False)
        original.update_required_long(9007199254740993)
        original.update_optional_long(-(2**63))
        original.update_optional_integer(-(2**31))
        original.update_optional_decimal(Decimal("-0.00"))
        original.update_required_time(time(23, 59, 59, 123456))
        original.update_required_datetime(datetime(2024, 2, 29, 12, 34, 56, 789000, timezone.utc))
        await original.audit_as("create exact generated entity JSON fixture").save(context)
        loaded = await load(original.id)
        expected = scalar_values(loaded)
        check(expected["required_date"] == date(2024, 2, 29), "SQLite native calendar date")
        check(expected["required_long"] == 9007199254740993, "SQLite exact Long beyond JavaScript precision")
        check(expected["required_time"] == time(23, 59, 59, 123456), "SQLite native microsecond Time")
        check(expected["required_datetime"] == datetime(2024, 2, 29, 12, 34, 56, 789000, timezone.utc), "SQLite UTC millisecond DateTime")

        for profile in JsonFieldNamingProfile:
            before = observed.calls.copy()
            wire = loaded.to_json(profile=profile)
            document = json.loads(wire)
            decoded = ScalarTypeProbe.from_json(wire, profile=profile)
            actual = scalar_values(decoded)
            for name, value in expected.items():
                check(type(actual[name]) is type(value) and actual[name] == value,
                      profile.value + " native round trip " + name)
            check(document[profile.render("required_long")] == "9007199254740993", profile.value + " Long string")
            check(document[profile.render("required_decimal")] == "9007199254740993.123456789", profile.value + " exact Decimal string")
            check(document[profile.render("optional_decimal")] == "-0.00", profile.value + " Decimal negative-zero scale")
            check(document[profile.render("optional_string")] == "", profile.value + " empty string")
            check(document[profile.render("optional_boolean")] is False, profile.value + " false Boolean")
            check(document[profile.render("optional_date")] is None, profile.value + " loaded null")
            check(not any(name.startswith("_") for name in document), profile.value + " no private state")
            check(observed.calls == before, profile.value + " JSON and E use no provider I/O")

        sparse = await (Q.scalar_type_probes_minimal().with_id_is(original.id).select_required_string().limit(1)
                        .comment("load a sparse entity JSON fixture")
                        .purpose("preserve omitted fields as NotLoaded").execute_for_one(context))
        sparse_wire = sparse.to_json()
        sparse_document = json.loads(sparse_wire)
        check(set(sparse_document) == {"id", "version", "requiredString"}, "sparse JSON includes only selected fields")
        restored_sparse = ScalarTypeProbe.from_json(sparse_wire)
        not_loaded(lambda: E.scalar_type_probe(restored_sparse).optional_decimal().eval(), "sparse optional field is NotLoaded, not null")
        restored_sparse.update_required_string(marker + "-forbidden")
        before = observed.calls.copy()
        try:
            await restored_sparse.audit_as("reject editing a partially loaded JSON entity").save(context)
        except CheckException:
            check(observed.calls == before, "partial JSON save rejected before provider I/O")
        else:
            raise AssertionError("partially loaded JSON entity was saved")

        reverse = await (Q.type_platforms_minimal().with_id_is(1).limit(1)
                         .select_scalar_type_probe_list_with(
                             Q.scalar_type_probes_minimal().with_id_is(original.id)
                             .select_required_string().select_required_decimal().order_by_id_ascending().limit(1))
                         .comment("load a bounded reverse entity JSON tree")
                         .purpose("verify typed nested JSON without hidden loading").execute_for_one(context))
        before = observed.calls.copy()
        reverse_wire = reverse.to_json()
        restored_reverse = TypePlatform.from_json(reverse_wire)
        reverse_e = E.type_platform(restored_reverse)
        check(reverse_e.scalar_type_probe_list().size().eval() == 1, "typed reverse JSON list")
        check(reverse_e.scalar_type_probe_list().first().required_decimal().eval() == expected["required_decimal"], "typed nested Decimal")
        not_loaded(lambda: reverse_e.scalar_type_probe_list().first().required_long().eval(), "nested sparse Long remains NotLoaded")
        not_loaded(lambda: reverse_e.name().eval(), "parent sparse name remains NotLoaded")
        check(observed.calls == before, "nested JSON and E use no provider I/O")

        forward = await (Q.scalar_type_probes_minimal().with_id_is(original.id).limit(1)
                         .select_type_platform_with(Q.type_platforms_minimal().limit(1))
                         .comment("load a sparse forward entity JSON detail")
                         .purpose("preserve selected foreign identity and target projection").execute_for_one(context))
        before = observed.calls.copy()
        restored_forward = ScalarTypeProbe.from_json(forward.to_json())
        forward_e = E.scalar_type_probe(restored_forward)
        check(forward_e.type_platform_id().eval() == 1, "forward JSON FK retained")
        check(forward_e.type_platform().id().eval() == 1, "forward JSON typed target")
        not_loaded(lambda: forward_e.type_platform().name().eval(), "forward target name remains NotLoaded")
        check(observed.calls == before, "forward JSON uses no provider I/O")
        filtered = await (Q.scalar_type_probes_minimal().with_id_is(original.id).limit(1)
                          .select_type_platform_with(Q.type_platforms_minimal().with_id_is(999999999).limit(1))
                          .comment("exclude forward detail without changing its foreign identity")
                          .purpose("verify filtered detail stays NotLoaded after JSON").execute_for_one(context))
        not_loaded(lambda: E.scalar_type_probe(filtered).type_platform().name().eval(), "filtered original detail name is NotLoaded")
        filtered_e = E.scalar_type_probe(ScalarTypeProbe.from_json(filtered.to_json()))
        check(filtered_e.type_platform_id().eval() == 1, "filtered forward JSON FK retained")
        check(filtered_e.type_platform().id().eval() == 1, "filtered target identity remains known")
        not_loaded(lambda: filtered_e.type_platform().name().eval(), "filtered forward detail remains NotLoaded")

        for field in ("required_float", "required_double"):
            for value in (math.nan, math.inf, -math.inf):
                candidate = ScalarTypeProbe.from_json(loaded.to_json())
                if field == "required_float":
                    candidate.update_required_float(value)
                else:
                    candidate.update_required_double(value)
                before = observed.calls.copy()
                try:
                    candidate.to_json()
                except EntityJSONError as error:
                    check(error.location.model_path == field and observed.calls == before,
                          field + " nonfinite encoding rejected with zero provider I/O " + str(value))
                else:
                    raise AssertionError("JSON accepted a nonfinite generated scalar")

        left = ScalarTypeProbe.from_json(loaded.to_json())
        right = ScalarTypeProbe.from_json(loaded.to_json())
        right.update_optional_string("pending-independent-right")
        left.update_optional_string("committed-independent-left")
        await left.audit_as("persist an independently decoded JSON mutation").save(context)
        readback = await load(original.id)
        check(readback.version == loaded.version + 1, "decoded JSON save advances version")
        check(E.scalar_type_probe(readback).optional_string().eval() == "committed-independent-left", "decoded JSON save persists only its own change")
        # The current provider rejects stale versions with no persisted record.
        # This proves boundaries are independent, not a complete error taxonomy.
        try:
            await right.audit_as("reject a stale independently decoded JSON mutation").save(context)
        except RuntimeError as error:
            check("did not return authoritative persisted state" in str(error), "independent JSON ledger preserves stale pending mutation")
        else:
            raise AssertionError("stale JSON save was silently discarded or accepted")
        final = await load(original.id)
        check(final.version == readback.version and E.scalar_type_probe(final).optional_string().eval() == "committed-independent-left", "stale JSON mutation leaves committed state unchanged")
        report = {"schema": "teaql.python-generated-entity-json-example/v1", "passed": True,
                  "profiles": [profile.value for profile in JsonFieldNamingProfile],
                  "checks": checks, "checkCount": len(checks), "providerCalls": dict(observed.calls),
                  "entityId": str(original.id), "finalVersion": final.version,
                  "limitations": ["Entity JSON is not transport authorization or a context-bound reference adapter",
                                  "Query/facet metadata is not an entity document",
                                  "Stale-save diagnostic taxonomy is not qualified by this example"]}
        report_path = Path(os.environ["TEAQL_SCALAR_PROBE_DB"] + ".json-" + uuid4().hex + ".report.json")
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print("PYTHON_ENTITY_JSON=" + json.dumps(report, ensure_ascii=False))
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
