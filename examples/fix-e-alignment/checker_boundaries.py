"""Current source + unchanged generated Q/E: real JSON and Checker save boundaries.

No INSERT/UPDATE SQL, generated implementation discovery, or manual seed data.
The controller owns the fresh evidence directory and retains the SQLite store.
"""
import argparse
import asyncio
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys


async def run(source, output, fixture):
    manifest = json.loads((fixture / "fixture-manifest.json").read_text())
    assert manifest["evaluationErrors"] == 0
    assert hashlib.sha256((fixture / "model.xml").read_bytes()).hexdigest() == manifest["modelSha256"]
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((fixture / "generated" / name).read_bytes()).hexdigest() == digest
    sys.path[:0] = [str(source / "src"), str(fixture / "generated")]
    import aiosqlite
    import teaql.runtime.context as implementation
    from teaql.core.value import Value
    from teaql.data_service import SQLiteTeaQLClient
    from teaql.provider.sqlite._decimal import DecimalConnection
    from teaql.provider.sqlite.transport import SqliteTransport
    from teaql.runtime import (CheckException, ContextEntityRef, FixedBusinessClock,
        JsonFieldNamingProfile, TeaQLNotLoadedError, UserContext, WireInputError,
        create_wire_entity_metadata, normalize_wire_input, retain_submitted_paths)
    from E import E
    from Q import Q
    from runtime_module import GENERATED_RUNTIME_MODULE
    assert Path(implementation.__file__).resolve() == source / "src/teaql/runtime/context.py"
    q_origin, e_origin = Path(sys.modules["Q"].__file__).resolve(), Path(sys.modules["E"].__file__).resolve()
    assert q_origin == fixture / "generated/Q.py" and e_origin == fixture / "generated/E.py"
    print("PYTHON_CHECKER_BOUNDARY_ORIGIN=" + json.dumps({"context": implementation.__file__,
        "contextSha256": hashlib.sha256(Path(implementation.__file__).read_bytes()).hexdigest(),
        "Q": str(q_origin), "E": str(e_origin), "aiosqlite": aiosqlite.__file__, "modelSha256": manifest["modelSha256"]}))

    counts = Counter({k: 0 for k in ("connections", "authorizations", "statements", "parentInserts", "childInserts",
                                     "query", "mutate", "begin", "next_id")})
    checker_calls = Counter()
    stages = Counter(mapped=0, save=0)
    fix = {"mode": None}

    def authorize(*_):
        counts["authorizations"] += 1
        return sqlite3.SQLITE_OK

    def trace(statement):
        counts["statements"] += 1
        # Classify the operation only; expanded SQL and values are never retained.
        if re.match(r'^\s*INSERT\s+INTO\s+["`\[]?purchase_order_data\b', statement, re.I):
            counts["parentInserts"] += 1
        if re.match(r'^\s*INSERT\s+INTO\s+["`\[]?order_item_data\b', statement, re.I):
            counts["childInserts"] += 1

    class Transport(SqliteTransport):
        def _connect(self):
            counts["connections"] += 1

            class Connection(DecimalConnection):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.set_authorizer(authorize)
                    self.set_trace_callback(trace)
            return aiosqlite.connect(self.db_path, factory=Connection)

    class ObservedService:
        def __init__(self, client): self.client = client
        def __getattr__(self, name): return getattr(self.client, name)
        async def query(self, *a, **kw):
            counts["query"] += 1
            return await self.client.query(*a, **kw)
        async def mutate(self, *a, **kw):
            counts["mutate"] += 1
            return await self.client.mutate(*a, **kw)
        async def begin(self, *a, **kw):
            counts["begin"] += 1
            return await self.client.begin(*a, **kw)
        async def next_id(self, *a, **kw):
            counts["next_id"] += 1
            return await self.client.next_id(*a, **kw)

    def setup(database):
        client = SQLiteTeaQLClient(str(database)); client.transport = Transport(str(database))
        context = (UserContext.new().install(GENERATED_RUNTIME_MODULE)
            .insert_resource("dataService", ObservedService(client))
            .with_active_root(ContextEntityRef("Tenant", 1))
            .with_business_clock(FixedBusinessClock(datetime(2032, 2, 29, tzinfo=timezone.utc))))
        original = context.require_resource("checker_registry")

        class Registry:
            def checker(self, entity):
                delegate = original.checker(entity)
                if delegate is None: return None
                class Checker:
                    def check_and_fix(self, ctx, record, location, results):
                        checker_calls[entity] += 1
                        if entity == "OrderItem" and fix["mode"]:
                            record["unit_price"] = Value.Decimal(Decimal("0" if fix["mode"] == "reject" else "12.34"))
                            record["product_name"] = Value.Null() if fix["mode"] == "reject" else Value.Text("Fixed child")
                        delegate.check_and_fix(ctx, record, location, results)
                return Checker()
        context.with_checker_registry(Registry())
        return context, client

    async def parent(context):
        row = ((await Q.purchase_orders().comment("Prepare the Checker boundary order")
            .purpose("Verify generated audited persistence boundaries").new_entity(context)))
        row.update_contact_phone("5550100").update_internal_note(None)
        return row

    async def child(context):
        row = ((await Q.order_items().comment("Prepare the Checker boundary item")
            .purpose("Verify generated required references and numeric constraints").new_entity(context)))
        row.update_product_name("Boundary item").update_unit_price(Decimal("10.00"))
        return row

    async def graph(context):
        p, c = (await parent(context)), (await child(context)); p.order_item_list().append(c)
        return p, c

    def clean(context):
        assert context.get_resource("fix_time") is None and context.get_resource("fix_operation") is None
        assert context._graph_save_guard.get() is None and not context._graph_save_lock.locked()

    observations = []
    def emit(round_number, name, **facts):
        row = {"round": round_number, "case": name, "passed": True, **facts}
        observations.append(row); print("PYTHON_CHECKER_BOUNDARY_CASE=" + json.dumps(row, default=str))

    async def rejected(context, entity, expected):
        before = counts.copy(); checks = checker_calls.copy()
        try:
            await entity.audit_as("Reject invalid input at the ordinary generated save boundary").save(context)
        except CheckException as error:
            assert counts == before, ("invalid save reached provider", dict(counts - before))
            clean(context)
            actual = {(v.rule_id, v.location.model_path) for v in error.violations}
            assert set(expected).issubset(actual), (expected, actual)
            return error, dict(checker_calls - checks)
        raise AssertionError("Invalid generated save was accepted")

    dry_database = output / "never-created.sqlite"
    dry, dry_client = setup(dry_database)
    class DryAllocator:
        def __init__(self): self.levels = {}
        async def next_id(self, entity):
            self.levels[entity] = self.levels.get(entity, 0) + 1
            return self.levels[entity]
        async def ensure_id_floor(self, entity, floor):
            self.levels[entity] = max(self.levels.get(entity, 0), floor)
    # Creation still reserves through Context. This no-schema Checker case
    # deliberately selects memory allocation to preserve its zero-SQL oracle.
    dry.with_internal_id_allocator(DryAllocator())
    before = counts.copy()
    checks = checker_calls.copy()
    await rejected(dry, (await parent(dry)).update_contact_phone("X" * 33), [("max_length", "contact_phone")])
    assert counts == before and not dry_database.exists()
    assert checker_calls["PurchaseOrder"] > checks["PurchaseOrder"]
    emit(0, "module-checker-without-schema", schemaCalled=False, databaseCreated=False,
         installedCheckerInvocations=checker_calls["PurchaseOrder"], zeroIO=True)
    await dry_client.close()

    database = output / "fixture.sqlite"
    context, client = setup(database)
    try:
        await context.ensure_schema()
        for round_number in (1, 2):
            owner, item = (await graph(context)); before = counts.copy()
            await owner.audit_as("Persist the positive boundary graph control").save(context)
            delta = counts - before
            assert delta["parentInserts"] == delta["childInserts"] == 1
            emit(round_number, "exact-provider-calibration", parentID=owner.id, childID=item.id,
                 parentInserts=delta["parentInserts"], childInserts=delta["childInserts"])

            await rejected(context, (await child(context)), [("required", "purchase_order")])
            emit(round_number, "required-relation", rule="required", modelPath="purchase_order", zeroIO=True)

            owner.update_contact_phone(None)
            await rejected(context, owner, [("required", "contact_phone")])
            assert owner.version == 1
            owner.update_contact_phone("5550100")
            emit(round_number, "required-null-update", version=owner.version, zeroIO=True)

            sparse = await (Q.purchase_orders_minimal().with_id_is(owner.id).limit(1)
                .select_tenant_with(Q.tenants_minimal().limit(1).comment("Load the modeled root reference"))
                .comment("Load a partial row with its correct modeled root")
                .purpose("Distinguish non-root completeness from root admission").execute_for_one(context))
            assert E.purchase_order(sparse).tenant_id().eval() == 1
            try: E.purchase_order(sparse).internal_note().eval()
            except TeaQLNotLoadedError: pass
            else: raise AssertionError("The optional non-root field was unexpectedly loaded")
            sparse.update_contact_phone("5550101")
            await rejected(context, sparse, [("invalid_type", "internal_note")])
            emit(round_number, "nonroot-partial-update", loadedRoot=1, absentField="internal_note", zeroIO=True)

            for name, change, rule, field in [
                ("minimum-number", lambda p, c: c.update_unit_price(Decimal("0")), "min", "unit_price"),
                ("maximum-number", lambda p, c: c.update_unit_price(Decimal("1000001")), "max", "unit_price"),
                ("minimum-string", lambda p, c: c.update_product_name(""), "min_length", "product_name"),
                ("maximum-string", lambda p, c: c.update_product_name("X" * 81), "max_length", "product_name"),
            ]:
                p, c = (await graph(context)); change(p, c)
                error, _ = await rejected(context, p, [(rule, "order_item_list[0]." + field)])
                v = next(v for v in error.violations if v.rule_id == rule)
                native = str(v.location)
                assert native == v.location.native_path == "order_item_list[0]." + field
                assert v.entity_type == "OrderItem"
                emit(round_number, name, rule=rule, nativeLocation=native, entityType=v.entity_type,
                     wire=v.to_wire(), zeroIO=True)

            p, c = (await graph(context)); fix["mode"] = "reject"
            await rejected(context, p, [("required", "order_item_list[0].product_name"), ("min", "order_item_list[0].unit_price")])
            assert E.order_item(c).unit_price().eval() == Decimal("10.00")
            assert E.order_item(c).product_name().eval() == "Boundary item"
            emit(round_number, "post-fix-rejection", originalPrice="10.00", fixedPrice="0", zeroIO=True, originalInputRetained=True)
            c.update_product_name(None).update_unit_price(Decimal("0")); fix["mode"] = "repair"
            before = counts.copy()
            await p.audit_as("Persist repaired required and range values on retry").save(context)
            delta = counts - before; fix["mode"] = None
            loaded = await (Q.order_items().with_id_is(c.id).limit(1).comment("Read the actual fixed item")
                .purpose("Prove post-Fix values reached persistence").execute_for_one(context))
            assert E.order_item(loaded).unit_price().eval() == Decimal("12.34")
            assert E.order_item(loaded).product_name().eval() == "Fixed child"
            assert delta["parentInserts"] == delta["childInserts"] == 1
            emit(round_number, "post-fix-repair-retry", parentID=p.id, childID=c.id, storedPrice="12.34",
                 storedName="Fixed child", parentInserts=1, childInserts=1)

            for profile_index, profile in enumerate(JsonFieldNamingProfile):
                meta = create_wire_entity_metadata("PurchaseOrder", ["contact_phone"], profile,
                    {"contact_phone": ["legacy/phone~"]})
                standard = profile.render("contact_phone")
                # Identity preparation is a separate service phase. The
                # observed JSON mapping/checker window must remain zero-I/O.
                obj = await parent(context)
                async def submit(text):
                    raw = json.loads(text)
                    normalized = normalize_wire_input(raw["payload/order"], meta, "/payload~1order")
                    stages["mapped"] += 1
                    obj.update_contact_phone(normalized.values["contact_phone"])
                    stages["save"] += 1
                    try: return await obj.audit_as("Save a normalized real JSON input").save(context)
                    except CheckException as error:
                        # The map derives from the actual JSON boundary, not a
                        # manually assigned source pointer on a synthetic error.
                        raise CheckException(retain_submitted_paths(error.violations, normalized)) from None

                before = counts.copy()
                try: await submit(json.dumps({"payload/order": {"legacy/phone~": None}}))
                except CheckException as error:
                    assert counts == before; v = error.violations[0]
                    assert v.rule_id == "required" and v.entity_type == "PurchaseOrder"
                    wires = {x.value: v.to_wire(x) for x in JsonFieldNamingProfile}
                    for x, wire in zip(JsonFieldNamingProfile, wires.values()):
                        assert wire["sourceInstancePath"] == "/payload~1order/legacy~1phone~0"
                        assert wire["instancePath"] == "/" + x.render("contact_phone")
                    emit(round_number, "accepted-input-alias", profile=profile.value, wires=wires, zeroIO=True)
                else: raise AssertionError("Alias bypassed required checking")

                for label, fields in [
                    ("unknown", {"unknown/field~": None}),
                    ("equal-forward", {standard: None, "legacy/phone~": None}),
                    ("equal-reverse", {"legacy/phone~": None, standard: None}),
                    ("unequal-forward", {standard: "a", "legacy/phone~": "b"}),
                    ("unequal-reverse", {"legacy/phone~": "b", standard: "a"}),
                ]:
                    before, before_checks, before_stages = counts.copy(), checker_calls.copy(), stages.copy()
                    try: await submit(json.dumps({"payload/order": fields}))
                    except WireInputError as error:
                        assert error.code == ("WIRE_UNKNOWN_FIELD" if label == "unknown" else "WIRE_FIELD_COLLISION")
                        expected_field = next(reversed(fields))
                        assert error.instance_path == "/payload~1order/" + expected_field.replace("~", "~0").replace("/", "~1")
                        assert counts == before and checker_calls == before_checks and stages == before_stages
                        emit(round_number, "input-" + label, profile=profile.value, code=error.code,
                             pointer=error.instance_path, checkerCalls=0, mapperCalls=0, saveCalls=0, zeroIO=True)
                    else: raise AssertionError("Invalid wire fields reached mapping/checking/save")
                before = counts.copy()
                row = await submit(json.dumps({"payload/order": {standard: "55509" + str(round_number) + str(profile_index)}}))
                assert (counts - before)["parentInserts"] == 1
                emit(round_number, "wire-positive-control", profile=profile.value, id=row.id, parentInserts=1)
            clean(context)
    finally:
        await client.close()

    with sqlite3.connect(database.resolve().as_uri() + "?immutable=1", uri=True) as db:
        rows = {name: list(db.execute(sql)) for name, sql in {
            "parents": "SELECT id,version,contact_phone FROM purchase_order_data ORDER BY id",
            "children": "SELECT id,version,purchase_order,product_name,unit_price FROM order_item_data ORDER BY id",
        }.items()}
    assert len(rows["parents"]) == 10 and len(rows["children"]) == 4
    assert not dry_database.exists()
    print("PYTHON_CHECKER_BOUNDARY_RESULT=" + json.dumps({"language": "python", "passed": True, "rounds": 2,
        "observedCases": len(observations), "sameDatabase": True, "physical": rows,
        "requiredAndRangeObserveActualFix": True, "realJsonInputAdapter": "application-owned-object-local-composition",
        "recursiveGeneratedHttpAdapterAccepted": False, "schemaFreeDatabaseCreated": False,
        "fullCheckerContractAccepted": False, "allP0P1Complete": False}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixture", type=Path)
    args = parser.parse_args()
    assert args.source.is_absolute() and args.output.is_absolute()
    assert args.output.is_dir() and not (args.output / "fixture.sqlite").exists()
    fixture = args.fixture or args.source / "examples/fix-e-alignment"
    asyncio.run(run(args.source.resolve(), args.output.resolve(), fixture.resolve()))
