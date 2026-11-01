"""One application, three evaluated model profiles; no diagnostic override."""
import asyncio
from collections import Counter
import json
import os
from pathlib import Path

from E import E
from Q import Q
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.data_service import SQLiteTeaQLClient
from teaql.runtime import TeaQLNotLoadedError, UserContext
import teaql


class ObservedService:
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


async def main():
    profile, round_number = os.environ["TEAQL_EXPRESSION_PROFILE"], int(os.environ["TEAQL_EXPRESSION_ROUND"])
    pointer = {"camelCase": "/scalarTypeProbeList", "snake_case": "/scalar_type_probe_list",
               "PascalCase": "/ScalarTypeProbeList"}[profile]
    suffix = {"camelCase": "/0/requiredString", "snake_case": "/0/required_string",
              "PascalCase": "/0/RequiredString"}[profile]
    client = SQLiteTeaQLClient(os.environ["TEAQL_EXPRESSION_DB"])
    observed = ObservedService(client)
    context = UserContext().install(GENERATED_RUNTIME_MODULE).insert_resource("dataService", observed)
    try:
        await context.ensure_schema()
        observed.calls.clear()
        row = await (Q.type_platforms().with_id_is(1).limit(1)
                     .comment("Load the root without its reverse list")
                     .purpose("Verify generated E diagnostics under the modeled JSON profile")
                     .execute_for_one(context))
        assert row is not None and E.type_platform(row).id().eval() == 1
        name = E.type_platform(row).name().eval()
        calibrated = observed.calls.copy()
        assert calibrated["query"] > 0, "the observer must measure the actual Q query"
        try:
            E.type_platform(row).scalar_type_probe_list().first().required_string().eval()
        except TeaQLNotLoadedError as error:
            wire, human = error.to_wire(), str(error)
        else:
            raise AssertionError("an unselected list must remain NotLoaded")
        location = [{"kind": "property", "name": "scalar_type_probe_list"}]
        assert wire["code"] == "NOT_LOADED"
        assert wire["location"] == location and wire["suggestedFix"] == {"action": "preload", "location": location}
        assert wire["attemptedLocation"] == location + [{"kind": "index", "index": 0}, {"kind": "property", "name": "required_string"}]
        assert wire["instancePath"] == pointer and wire["attemptedInstancePath"] == pointer + suffix
        assert wire["breakPoint"] == "scalar_type_probe_list" and wire["breakPointIndex"] == 0
        assert wire["originalExpression"] == "E.type_platform(<root>).scalar_type_probe_list().first().required_string().eval()"
        assert wire["expressionWithBrokenPoint"] == "E.type_platform(<root>).scalar_type_probe_list()<broken>.first().required_string().eval()"
        assert human.startswith("TeaQLNotLoadedError:") and "break_point=scalar_type_probe_list" in human
        assert "expression=" + wire["expressionWithBrokenPoint"] in human and '"instancePath"' not in human
        assert observed.calls == calibrated and E.type_platform(row).name().eval() == name
        print("GENERATED_E_MODEL_PROFILE=" + json.dumps({
            "language": "python", "profile": profile, "round": round_number, "passed": True,
            "wire": wire, "human": human, "providerEntries": 0, "queryCalibration": calibrated["query"],
            "selectedNameUnchanged": True, "runtimeOrigin": str(Path(teaql.__file__).resolve()),
        }))
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
