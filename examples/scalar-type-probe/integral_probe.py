"""Real generated Q/E saves: exact Integer/Long/FK checks before provider entry."""
import asyncio
from decimal import Decimal
import json
import os
import sqlite3
from uuid import uuid4

from E import E
from Q import Q
from main import new_probe
from json_roundtrip import ObservedService
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.core.value import Value
from teaql.data_service import SQLiteTeaQLClient
from teaql.runtime import CheckException, UserContext


class InjectedFix:
    def __init__(self, field, value):
        self.field, self.value, self.calls = field, value, 0

    def checker(self, entity):
        return self if entity == "ScalarTypeProbe" else None

    def check_and_fix(self, context, record, location, results):
        self.calls += 1
        record[self.field] = Value.from_any(self.value)


async def reload(context, identity):
    return await (Q.scalar_type_probes().with_id_is(identity).limit(1)
        .comment("reload exact integer values").purpose("verify mutation Q and E agree").execute_for_one(context))


async def main():
    database = os.environ["TEAQL_SCALAR_PROBE_DB"] + ".integrals.sqlite"
    service = ObservedService(SQLiteTeaQLClient(database))
    context = UserContext().install(GENERATED_RUNTIME_MODULE).insert_resource("dataService", service)
    original = context.get_resource("checker_registry")
    marker = "integral-" + uuid4().hex
    checks = []
    try:
        await context.ensure_schema()
        row = new_probe(context, marker, Decimal("3.50"))
        row.update_required_integer(2**31 - 1)
        row.update_required_long(2**63 - 1)
        await row.audit_as("calibrate exact integral provider observers").save(context)
        baseline = await reload(context, row.id)
        assert all(service.calls[name] > 0 for name in ("query", "begin", "next_id"))
        cases = [
            ("integer-positive-overflow", "required_integer", 2**31),
            ("integer-negative-overflow", "required_integer", -(2**31) - 1),
            ("optional-integer-positive-overflow", "optional_integer", Decimal(2**31)),
            ("optional-integer-negative-overflow", "optional_integer", Decimal(-(2**31) - 1)),
            ("fractional-long", "required_long", Decimal("12.75")),
            ("long-positive-overflow", "required_long", 2**63),
            ("long-negative-overflow", "required_long", -(2**63) - 1),
            ("long-float", "required_long", 12.0),
            ("long-text", "required_long", "PRIVATE_INVALID_INTEGER"),
            ("long-bool", "required_long", True),
            ("fractional-reference", "type_platform", Decimal("1.5")),
            ("negative-reference", "type_platform", -1),
            ("reference-overflow", "type_platform", 2**64),
            ("reference-float", "type_platform", 1.0),
            ("reference-text", "type_platform", "PRIVATE_INVALID_REFERENCE"),
            ("reference-bool", "type_platform", True),
        ]
        for operation in ("create", "update"):
            for name, field, value in cases:
                candidate = new_probe(context, marker, Decimal("3.50")) if operation == "create" else await reload(context, row.id)
                candidate.update_required_string("must not be committed")
                fix = InjectedFix(field, value)
                context.with_checker_registry(fix)
                before = dict(service.calls)
                try:
                    await candidate.audit_as("reject invalid integral Fix output before provider entry").save(context)
                except CheckException as error:
                    assert any(item.rule_id == "invalid_type" and item.location.model_path == field for item in error.violations)
                    assert "PRIVATE_INVALID" not in str(error)
                    for item in error.violations:
                        assert "inputValue" not in item.to_wire()
                        json.dumps(item.to_wire(), allow_nan=False)
                else:
                    raise AssertionError("invalid integral was persisted: " + name)
                finally:
                    context.with_checker_registry(original)
                assert service.calls == before and fix.calls == 1
                checks.append(operation + "/" + name)
        unchanged = await reload(context, row.id)
        assert unchanged.version == baseline.version == 1
        assert E.scalar_type_probe(unchanged).required_long().eval() == 2**63 - 1
        assert E.scalar_type_probe(unchanged).type_platform_id().eval() == 1
        for field, value in (("required_integer", 2**31), ("optional_integer", -(2**31) - 1)):
            for operation in ("create", "update"):
                candidate = new_probe(context, marker, Decimal("3.50")) if operation == "create" else await reload(context, row.id)
                getattr(candidate, "update_" + field)(value)
                before = dict(service.calls)
                try:
                    await candidate.audit_as("reject out-of-range native Integer updater").save(context)
                except CheckException as error:
                    assert any(item.rule_id == "invalid_type" and item.location.model_path == field for item in error.violations)
                else:
                    raise AssertionError("native Integer updater bypassed model width")
                assert service.calls == before
                checks.append(operation + "/native-" + field)
        # Equivalent valid custom Fix output proves the negative is type/range
        # validation, not a checker missing managed defaults or required fields.
        class Repair:
            def checker(self, entity):
                return self if entity == "ScalarTypeProbe" else None
            def check_and_fix(self, context, record, location, results):
                original.checker("ScalarTypeProbe").check_and_fix(context, record, location, results)
                record["required_long"] = Value.Decimal(Decimal("9223372036854775807.0"))
        context.with_checker_registry(Repair())
        valid = new_probe(context, marker, Decimal("3.50"))
        await valid.audit_as("persist exact integral Decimal from custom Fix").save(context)
        context.with_checker_registry(original)
        loaded = await reload(context, valid.id)
        assert type(E.scalar_type_probe(loaded).required_long().eval()) is int
        assert E.scalar_type_probe(loaded).required_long().eval() == 2**63 - 1
        for bad in (2**31, -(2**31) - 1, 1.5, "PRIVATE_INVALID_INTEGER"):
            with sqlite3.connect(database) as connection:
                connection.execute("UPDATE scalar_type_probe_data SET required_integer=? WHERE id=?", [bad, row.id])
            try:
                await reload(context, row.id)
            except ValueError as error:
                assert "invalid loaded Integer field ScalarTypeProbe.required_integer" in str(error)
                assert "PRIVATE_INVALID_INTEGER" not in str(error)
            else:
                raise AssertionError("generated Q silently accepted a corrupt Integer")
            checks.append("corrupt-read/" + type(bad).__name__ + "/" + str(len(checks)))
        with sqlite3.connect(database) as connection:
            connection.execute("UPDATE scalar_type_probe_data SET required_integer=? WHERE id=?", [2**31 - 1, row.id])
            oracle = connection.execute("SELECT version,required_integer,required_long,type_platform FROM scalar_type_probe_data WHERE id=?", [row.id]).fetchone()
        assert oracle == (1, 2**31 - 1, 2**63 - 1, 1)
        assert len(checks) == len(set(checks)) == 40
        print("PYTHON_INTEGRAL=" + json.dumps(dict(schema="teaql.python-generated-integral-example/v1",
            passed=True, checks=checks, checkCount=len(checks), entityId=str(row.id), validFixId=str(valid.id),
            invalidFixCases=32, nativeUpdaterCases=4, corruptReadCases=4,
            rejectionProviderCalls=dict(query=0, mutate=0, begin=0, next_id=0),
            calibrated=True, exactDecimalFixPersisted=True, oracle="|".join(map(str, oracle)))))
    finally:
        await service.close()


if __name__ == "__main__":
    asyncio.run(main())
