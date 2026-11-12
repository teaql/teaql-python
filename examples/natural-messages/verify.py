"""Automatic generated metadata, Q/E and audited saves on a local SQLite graph."""
import asyncio
from collections import Counter
from datetime import datetime, timezone
import inspect
import json
import os
from pathlib import Path
import sqlite3

import teaql
from teaql.data_service import SQLiteTeaQLClient
from teaql.runtime import (CheckException, CheckerMessageOutput, FixedBusinessClock,
    UserContext, standard_checker_message_renderer)
from E import E
from Q import Q
from runtime_module import GENERATED_RUNTIME_MODULE

SECRET = "密钥🔑" + "x" * 98  # 101 Unicode scalars, 102 UTF-16 code units.
REPO = Path(__file__).resolve().parents[2]


async def main():
    database = Path(os.environ["TEAQL_NATURAL_MESSAGES_DB"])
    fixture = REPO / "examples/natural-messages/fixture"
    assert Path(teaql.__file__).resolve() == REPO / "src/teaql/__init__.py"
    assert Path(inspect.getfile(Q)).resolve() == fixture / "Q.py"
    client = SQLiteTeaQLClient(str(database))
    context = (UserContext().install(GENERATED_RUNTIME_MODULE).insert_resource("dataService", client)
               .with_business_clock(FixedBusinessClock(datetime(2033, 1, 1, tzinfo=timezone.utc)))
               .install_checker_message_warning(lambda _: None))
    # Only normal generated module composition installs metadata and Checkers.
    model = context.capture_checker_messages().model
    assert model is GENERATED_RUNTIME_MODULE._checker_presentation
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
        assert context.entity("Entry").audit_mask_fields_val == ["name"]
        generated_checker = context.get_resource("checker_registry").checker("Entry")
        class Sink:
            def on_safe_event(self, ctx, event):
                events.append(event)
        context.with_app_audit_event_sink(Sink())
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
        parent_version = parent.version
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
        await reject(None, "en", "The name of the 2nd entry is required.")
        await reject(None, "zh-CN", "请填写第2项明细的名称。")
        await reject(SECRET, "en", "The name of the 2nd entry must not exceed 100 Unicode scalar values; its current length is 101.")
        custom_calls = []
        def renderer(request):
            custom_calls.append(request)
            assert request.arguments["input"] == "密钥" + "*" * 97 + "xx"
            assert request.arguments["input_len"] == "101"
            return CheckerMessageOutput("Private " + SECRET)
        context.install_checker_message_renderer(renderer)
        await reject(SECRET, "en", "Private [REDACTED]")
        assert len(custom_calls) == 1, "graph relocation must not call the customer renderer twice"
        context.install_checker_message_renderer(standard_checker_message_renderer)
        assert second.name == SECRET and second.version == version
        first.update_name("first")
        second.update_name("renamed")
        await parent.audit_as("Persist only the corrected second child").save(context)
        assert len(events) == audits + 1
        stored = await load(second.id)
        assert E.entry(stored).name().eval() == "renamed" and stored.version == version + 1
        assert parent.version == parent_version
        assert context.get_resource("checker_registry").checker("Entry") is generated_checker
        assert context.capture_checker_messages().model is model
        # Read-only storage oracle, not an alternative application mutation API.
        with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as db:
            assert db.execute("SELECT name,version FROM entry_data WHERE id=?", (second.id,)).fetchone() == ("renamed", version + 1)
        print("PY_NATURAL_SQLITE_PASS=" + json.dumps(dict(passed=True, first=first.id, child=second.id, version=stored.version,
            responses=len(responses), providerCallsOnRejection=0, transactionCallsOnRejection=0, updatedAudits=1,
            typedQ=True, typedE=True, automaticMetadata=True, originalGeneratedChecker=True,
            customerRendererCalls=len(custom_calls), unchangedParent=True)))
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
