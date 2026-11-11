"""Generated Q/E/audited-save Context Fix verification over real SQLite."""
import asyncio
from collections import Counter
from datetime import datetime, timezone
import inspect
import json
import os
from pathlib import Path
import sqlite3

import teaql
from teaql.core.value import Timestamp
from teaql.data_service import SQLiteTeaQLClient
from teaql.runtime import ContextFix, CheckException, FixedBusinessClock, UserContext
from E import E
from Q import Q
from runtime_module import GENERATED_RUNTIME_MODULE

A = datetime(2033, 1, 1, tzinfo=timezone.utc)
B = datetime(2033, 1, 2, tzinfo=timezone.utc)
C = datetime(2033, 1, 3, tzinfo=timezone.utc)


def millis(value):
    return value.millis if isinstance(value, Timestamp) else int(value.timestamp() * 1000)


async def rejected(work, path):
    try:
        await work
    except CheckException as error:
        assert any(item.entity_type and item.location.instance_path == path for item in error.violations), error.violations
        return error
    raise AssertionError("expected a structured Check failure")


async def main():
    database = Path(os.environ["TEAQL_CONTEXT_FIX_DB"])
    source = Path(os.environ["TEAQL_CONTEXT_FIX_SOURCE"])
    assert Path(teaql.__file__).resolve() == source / "src/teaql/__init__.py"
    assert Path(inspect.getfile(Q)).resolve() == Path(__file__).parent / "fixture/Q.py"
    client = SQLiteTeaQLClient(str(database))
    context = (UserContext().install(GENERATED_RUNTIME_MODULE).insert_resource("dataService", client)
               .with_business_clock(FixedBusinessClock(A)))
    calls, events, resolver_calls = Counter(), [], Counter()
    for name in ("enable_soundex", "verify_schema", "fetch_all_sql", "execute_sql", "begin_sql"):
        original = getattr(client.transport, name)
        async def counted(*args, _name=name, _original=original, **kwargs):
            calls[_name] += 1
            return await _original(*args, **kwargs)
        setattr(client.transport, name, counted)
    try:
        await context.ensure_schema()
        descriptor = context.entity("Entry")
        for field in ("source_ip", "opened_by", "last_ip", "changed_by"):
            prop = descriptor.property_by_name(field).on_create_from_context("identity")
            if field in ("last_ip", "changed_by"):
                prop.on_update_from_context("identity")
        registry = context.get_resource("checker_registry")
        generated = registry.checker("Entry")

        class Checker:
            def check_and_fix(self, ctx, record, location, results):
                for field in ("source_ip", "opened_by", "last_ip", "changed_by"):
                    if ctx.get_resource("fix_operation") != "insert" and field in ("source_ip", "opened_by"):
                        continue
                    ContextFix.apply(ctx, record, field, "identity")
                generated.check_and_fix(ctx, record, location, results)

        class Registry:
            def checker(self, entity):
                return Checker() if entity == "Entry" else registry.checker(entity)

        class Sink:
            def on_safe_event(self, ctx, event):
                events.append(event)

        context.with_checker_registry(Registry()).with_app_audit_event_sink(Sink())
        phase, fail_token, invalid_ip = "A", False, False

        def resolver(ctx, request):
            resolver_calls[(request.operation, request.field)] += 1
            if request.function == "now":
                return request.now
            if request.function == "uniStr":
                if fail_token:
                    raise RuntimeError("PRIVATE_CONTEXT_PROVIDER_CANARY")
                return "fixture-token"
            return "x" * 101 if invalid_ip and request.field == "last_ip" else phase + ":" + request.field

        context.insert_resource("context_fix_resolver", resolver)

        def make(name):
            return (Q.entries().comment("Prepare one Context fixture entity")
                    .purpose("Verify automatic values cannot create mutations").new_entity(context)
                    .update_name(name).update_catalog(1))

        async def load(identity):
            rows = await (Q.entries().with_id_is(identity).limit(1).comment("Reload stored Context fixture")
                          .purpose("Observe committed values through generated Q and E").execute_for_list(context))
            assert len(rows) == 1
            return rows[0]

        broken = make("failed token")
        fail_token = True
        calls.clear()
        error = await rejected(broken.audit_as("Reject failed Context provider").save(context), "/guardedToken")
        assert "PRIVATE_CONTEXT_PROVIDER_CANARY" not in str(error)
        assert not calls and not events and broken.bornAt is None and broken.name == "failed token"
        fail_token = False
        first, second = make("first"), make("second")
        resolver_calls.clear()
        await first.audit_as("Create first row under Context A").save(context)
        assert resolver_calls[("insert", "guarded_token")] == 1
        assert resolver_calls[("insert", "touched_at")] == 1
        await second.audit_as("Create independent Context A sibling").save(context)
        first = await load(first.id)
        identity, original_version = first.id, first.version
        assert millis(E.entry(first).born_at().eval()) == millis(A)
        assert E.entry(first).last_ip().eval() == "A:last_ip"

        phase = "B"
        context.with_business_clock(FixedBusinessClock(B))
        audits = len(events)
        calls.clear()
        resolver_calls.clear()
        for _ in range(2):
            await first.audit_as("Save unchanged row under Context B").save(context)
        assert not calls and not resolver_calls and len(events) == audits
        stored = await load(identity)
        assert stored.version == original_version and stored.lastIp == "A:last_ip" and millis(stored.touchedAt) == millis(A)

        first.update_name("n" * 101)
        calls.clear()
        await rejected(first.audit_as("Reject invalid business value").save(context), "/name")
        assert not calls and len(events) == audits and first.name == "n" * 101
        first.update_name("first")
        await first.audit_as("Revert the failed edit without an update").save(context)
        assert not calls and len(events) == audits
        first.update_name("renamed")
        invalid_ip = True
        await rejected(first.audit_as("Reject invalid automatic IP").save(context), "/lastIp")
        assert not calls and first.lastIp == "A:last_ip" and first.name == "renamed"
        invalid_ip = False
        resolver_calls.clear()
        await first.audit_as("Commit one independently changed business field").save(context)
        assert len(events) == audits + 1 and resolver_calls[("update", "touched_at")] == 1
        stored = await load(identity)
        assert E.entry(stored).name().eval() == "renamed" and stored.version == original_version + 1
        assert millis(stored.bornAt) == millis(A) and millis(stored.touchedAt) == millis(B)
        assert stored.sourceIp == "A:source_ip" and stored.openedBy == "A:opened_by"
        assert stored.lastIp == "B:last_ip" and stored.changedBy == "B:changed_by"

        parents = await (Q.catalogs().with_id_is(1).limit(1).comment("Load unchanged graph ancestor")
                         .purpose("Verify graph-wide Context rollback and retry").execute_for_list(context))
        assert len(parents) == 1
        parent = parents[0]
        parent_version = parent.version
        first, second = await load(identity), await load(second.id)
        parent.entry_list().extend((first, second))
        first.update_name("graph edit")
        second.update_name("z" * 101)
        phase = "C"
        context.with_business_clock(FixedBusinessClock(C))
        audits = len(events)
        calls.clear()
        await rejected(parent.audit_as("Reject later child after preparing sibling").save(context), "/entryList/1/name")
        assert not calls and len(events) == audits
        assert first.name == "graph edit" and first.lastIp == "B:last_ip"
        changed = dict(first._entity_root.current_change_set().changes())[first._teaql_entity_key()]
        assert set(changed) == {"name"}, changed
        second.update_name("second")
        await parent.audit_as("Retry with just one dirty child").save(context)
        assert len(events) == audits + 1 and parent.version == parent_version
        assert (await load(identity)).lastIp == "C:last_ip" and (await load(second.id)).lastIp == "A:last_ip"
        # Independent, read-only storage oracle; no seed or mutation SQL.
        with sqlite3.connect(database.resolve().as_uri() + "?mode=ro&immutable=1", uri=True) as db:
            row = db.execute("SELECT name,last_ip,source_ip,version FROM entry_data WHERE id=?", (identity,)).fetchone()
        assert row == ("graph edit", "C:last_ip", "A:source_ip", original_version + 2)
        print("PYTHON_CONTEXT_FIX_SQLITE=" + json.dumps(dict(passed=True, typedQ=True, typedE=True,
              noOpProviderCalls=0, failedCheckProviderCalls=0, updateAudits=1, objectLocation=True,
              graphRollback=True, fixOnce=True)))
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
