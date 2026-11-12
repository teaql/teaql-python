"""Generated Q/E/audited-save natural messages over an unchanged SQLite fixture."""
import asyncio
from collections import Counter
from datetime import datetime, timezone
import inspect
import json
import os
from pathlib import Path
import sqlite3

import teaql
from teaql.core.value import Value
from teaql.data_service import SQLiteTeaQLClient
from teaql.runtime import CheckException, CheckResult, CheckerPresentationModel, ContextFix, FixedBusinessClock, ObjectLocation, UserContext
from E import E
from Q import Q
from runtime_module import GENERATED_RUNTIME_MODULE

SECRET = "密钥🔑abcdef"  # Nine Unicode scalar values, ten UTF-16 code units.
REPO = Path(__file__).resolve().parents[2]


async def main():
    database = Path(os.environ["TEAQL_NATURAL_MESSAGES_DB"])
    fixture = REPO / "examples/context-derived/fixture"
    assert Path(teaql.__file__).resolve() == REPO / "src/teaql/__init__.py"
    assert Path(inspect.getfile(Q)).resolve() == fixture / "Q.py"
    client = SQLiteTeaQLClient(str(database))
    context = (UserContext().install(GENERATED_RUNTIME_MODULE).insert_resource("dataService", client)
               .with_business_clock(FixedBusinessClock(datetime(2033, 1, 1, tzinfo=timezone.utc)))
               .install_checker_message_warning(lambda _: None))
    data = json.loads((REPO / "tests/fixtures/natural-messages/cases-v1.json").read_text())
    model = CheckerPresentationModel.from_json(json.dumps({"schema": "teaql.checker-model/v1", "revision": "generated-natural-example-v1",
        "entities": {key: data["entities"][key] for key in ("Catalog", "Entry")}, "currentObject": data["currentObject"]}))
    context.install_checker_presentation_model(model)
    calls, events = Counter(), []
    for name in ("enable_soundex", "verify_schema", "fetch_all_sql", "execute_sql", "begin_sql"):
        original = getattr(client.transport, name)
        async def counted(*args, _name=name, _original=original, **kwargs):
            calls[_name] += 1
            return await _original(*args, **kwargs)
        setattr(client.transport, name, counted)
    try:
        await context.ensure_schema()
        await context.ensure_schema()
        context.entity("Entry").audit_mask_fields(["name"])
        for field in ("source_ip", "last_ip", "opened_by", "changed_by"):
            context.entity("Entry").property_by_name(field).on_create_from_context("identity")
        def resolver(ctx, request):
            return request.now if request.function == "now" else "fixture-token" if request.function == "uniStr" else "local"
        context.insert_resource("context_fix_resolver", resolver)
        registry = context.get_resource("checker_registry")
        generated = registry.checker("Entry")
        class Checker:
            def check_and_fix(self, ctx, record, loc, results):
                if ctx.get_resource("fix_operation") == "insert":
                    for field in ("source_ip", "last_ip", "opened_by", "changed_by"):
                        ContextFix.apply(ctx, record, field, "identity")
                generated.check_and_fix(ctx, record, loc, results)
                name = record.get("name")
                name = name.val if isinstance(name, Value) else name
                path = (loc or ObjectLocation()).property("name")
                if type(name) is str and not name.strip() and not any(str(r.rule_id).lower() == "required" and r.location == path for r in results):
                    results.append(CheckResult("required", path))
                if type(name) is str and len(name) > 8:
                    results.append(CheckResult("max_length", path, name, 8))
        class Registry:
            def checker(self, entity):
                return Checker() if entity == "Entry" else registry.checker(entity)
        class Sink:
            def on_safe_event(self, ctx, event):
                events.append(event)
        context.with_checker_registry(Registry()).with_app_audit_event_sink(Sink())
        def make(name):
            return (Q.entries().comment("Prepare one natural-message example child")
                .purpose("Verify generated audited mutations and located messages").new_entity(context).update_name(name).update_catalog(1))
        async def load(identity):
            rows = await (Q.entries().with_id_is(identity).limit(1).comment("Reload complete example child")
                .purpose("Verify stored values through typed E").execute_for_list(context))
            assert len(rows) == 1
            return rows[0]
        first, second = make("first"), make("second")
        await first.audit_as("Create the first example child").save(context)
        await second.audit_as("Create the second example child").save(context)
        first, second = await load(first.id), await load(second.id)
        version = second.version
        assert E.entry(second).name().eval() == "second"
        parents = await (Q.catalogs().with_id_is(1).limit(1).comment("Load unchanged graph owner")
            .purpose("Locate errors in the second child").execute_for_list(context))
        assert len(parents) == 1
        parent = parents[0]
        parent.entry_list().extend((first, second))
        first.update_name("changed")
        audits = len(events)
        responses = []
        async def reject(value, locale, expected):
            context.set_locale_code(locale)
            second.update_name(value)
            calls.clear()
            try:
                await parent.audit_as("Reject the second child before SQL or audit").save(context)
            except CheckException as error:
                response = {"violations": [r.to_wire() for r in error.violations]}
                assert any(v["instancePath"] == "/entryList/1/name" and v["entityType"] == "Entry" and v["message"] == expected for v in response["violations"]), error
                assert expected in str(error) and expected in error.args[0]
                assert SECRET not in json.dumps(response, ensure_ascii=False) + str(error) + repr(error.args)
                assert not calls and len(events) == audits, (calls, len(events))
                responses.append(response)
                print("PY_NATURAL_RESPONSE=" + json.dumps(response, ensure_ascii=False))
            else:
                raise AssertionError("expected a structured CheckException")
        await reject("", "en", "The name of the 2nd entry is required.")
        await reject("", "zh-CN", "请填写第2条明细的名称。")
        await reject(SECRET, "en", "The name of the 2nd entry must not exceed 8 Unicode scalar values; its current length is 9.")
        assert second.name == SECRET and second.version == version
        first.update_name("first")
        second.update_name("renamed")
        await parent.audit_as("Persist only the corrected second child").save(context)
        assert len(events) == audits + 1
        stored = await load(second.id)
        assert E.entry(stored).name().eval() == "renamed" and stored.version == version + 1
        # Read-only storage oracle, not an alternative application mutation API.
        with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as db:
            assert db.execute("SELECT name,version FROM entry_data WHERE id=?", (second.id,)).fetchone() == ("renamed", version + 1)
        print("PY_NATURAL_SQLITE_PASS=" + json.dumps(dict(passed=True, first=first.id, child=second.id, version=stored.version,
            responses=len(responses), providerCallsOnRejection=0, transactionCallsOnRejection=0, updatedAudits=1, typedQ=True, typedE=True)))
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
