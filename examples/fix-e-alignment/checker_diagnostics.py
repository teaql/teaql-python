"""Real generated-save Checker metadata probe on the retained three-entity model.

The caller owns the NEW database path. No generated source is edited, no SQL
values are collected, and no test database is deleted. Both rounds share one
context and database, including after rejected saves.
"""
import argparse
import asyncio
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sqlite3
import sys


async def verify(database):
    example = Path(__file__).resolve().parent
    manifest = json.loads((example / "fixture-manifest.json").read_text())
    generated = example / "generated"
    assert manifest["evaluationErrors"] == 0
    assert hashlib.sha256((example / "model.xml").read_bytes()).hexdigest() == manifest["modelSha256"]
    actual = {str(p.relative_to(generated)) for p in generated.rglob("*")
              if p.is_file() and p.suffix != ".pyc"}
    assert actual == set(manifest["files"])
    for name, expected in manifest["files"].items():
        assert not (generated / name).is_symlink()
        assert hashlib.sha256((generated / name).read_bytes()).hexdigest() == expected
    sys.path.insert(0, str(example.parents[1] / "src"))
    sys.path.insert(0, str(generated))
    from E import E
    from Q import Q
    from runtime_module import GENERATED_RUNTIME_MODULE
    import aiosqlite
    from teaql.data_service import SQLiteTeaQLClient
    from teaql.provider.sqlite._decimal import DecimalConnection
    from teaql.provider.sqlite.transport import SqliteTransport
    from teaql.runtime import (CheckException, CheckResult, ContextEntityRef, FixedBusinessClock,
                               JsonFieldNamingProfile, ObjectLocation, UserContext)
    import teaql.runtime.context as runtime_context
    assert Path(runtime_context.__file__).resolve() == example.parents[1] / "src/teaql/runtime/context.py"

    counts = Counter()

    class Transport(SqliteTransport):
        def _connect(self):
            counts["connections"] += 1

            class Connection(DecimalConnection):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.set_authorizer(authorize)
                    self.set_trace_callback(trace)

            return aiosqlite.connect(self.db_path, factory=Connection)

    def authorize(*args):
        counts["authorizations"] += 1
        return sqlite3.SQLITE_OK

    def trace(statement):
        counts["statements"] += 1  # Do not retain expanded SQL or field values.

    client = SQLiteTeaQLClient(str(database))
    client.transport = Transport(str(database))
    context = (UserContext.new().install(GENERATED_RUNTIME_MODULE)
               .insert_resource("dataService", client)
               .with_business_clock(FixedBusinessClock(datetime(2032, 2, 29, tzinfo=timezone.utc)))
               .with_active_root(ContextEntityRef("Tenant", 1)))
    await context.ensure_schema()
    observations, failures = [], []

    def graph():
        parent = (Q.purchase_orders().comment("Prepare Checker diagnostic order")
                  .purpose("Verify ordinary generated save rejects invalid input").new_entity(context))
        parent.update_contact_phone("5550100").update_internal_note(None)
        child = (Q.order_items().comment("Prepare Checker diagnostic child")
                 .purpose("Verify nested violations retain their declaring type").new_entity(context))
        child.update_product_name("Synthetic checker item").update_unit_price(Decimal("10.00"))
        parent.order_item_list().append(child)
        return parent, child

    def clean():
        assert context.get_resource("fix_time") is None
        assert context.get_resource("fix_operation") is None
        assert context._graph_save_guard.get() is None
        assert not context._graph_save_lock.locked()

    for round_number in (1, 2):
        context.set_locale_code("en")
        parent, child = graph()
        before = counts.copy()
        saved = await parent.audit_as("Persist the valid Checker observation control").save(context)
        assert all(counts[name] > before[name] for name in ("connections", "authorizations", "statements"))
        loaded = await (Q.purchase_orders().with_id_is(saved.id).limit(1)
                        .comment("Read the successful Checker control")
                        .purpose("Calibrate Q E and the physical SQLite observer").execute_for_one(context))
        assert E.purchase_order(loaded).contact_phone().eval() == "5550100"
        assert E.order_item(child).unit_price().eval() == Decimal("10.00")
        clean()
        cases = [
            ("parent_required", "PurchaseOrder", "contact_phone", "required", "en",
             lambda p, c: p.update_contact_phone(None)),
            ("child_required", "OrderItem", "order_item_list[0].product_name", "required", "en",
             lambda p, c: c.update_product_name(None)),
            ("parent_length", "PurchaseOrder", "contact_phone", "max_length", "en",
             lambda p, c: p.update_contact_phone("x" * 33)),
            ("child_length", "OrderItem", "order_item_list[0].product_name", "max_length", "en",
             lambda p, c: c.update_product_name("x" * 81)),
            ("child_range", "OrderItem", "order_item_list[0].unit_price", "max", "en",
             lambda p, c: c.update_unit_price(Decimal("1000001"))),
            ("localized_required", "PurchaseOrder", "contact_phone", "required", "zh-CN",
             lambda p, c: p.update_contact_phone(None)),
        ]
        for name, expected_type, expected_path, expected_rule, locale, change in cases:
            parent, child = graph()
            change(parent, child)
            context.set_locale_code(locale)
            before = counts.copy()
            try:
                await parent.audit_as("Reject synthetic invalid Checker input").save(context)
            except CheckException as error:
                assert counts == before, (name, "invalid input performed SQLite I/O")
                clean()
                assert len(error.violations) == 1, (name, error.violations)
                violation = error.violations[0]
                assert violation.rule_id == expected_rule
                assert violation.location.model_path == expected_path
                assert violation.message and not violation.message.startswith("checker.")
                wires = {profile.value: violation.to_wire(profile) for profile in JsonFieldNamingProfile}
                field_pointers = {"contact_phone": ("contactPhone", "contact_phone", "ContactPhone"),
                                  "product_name": ("productName", "product_name", "ProductName"),
                                  "unit_price": ("unitPrice", "unit_price", "UnitPrice")}
                for index, profile in enumerate(JsonFieldNamingProfile):
                    field_name = expected_path.rsplit(".", 1)[-1]
                    prefix = ("/orderItemList/0", "/order_item_list/0", "/OrderItemList/0")[index] if "." in expected_path else ""
                    assert wires[profile.value]["instancePath"] == prefix + "/" + field_pointers[field_name][index]
                # Persist every actual observation before failing the metadata
                # assertion, so the negative run exposes all affected paths.
                observations.append({"round": round_number, "case": name, "locale": locale,
                                     "expectedEntityType": expected_type, "wires": wires,
                                     "zeroSQLiteIO": True})
                if violation.entity_type != expected_type:
                    failures.append({"round": round_number, "case": name,
                                     "expected": expected_type, "actual": violation.entity_type})
            else:
                raise AssertionError((name, "invalid generated save succeeded"))

        partial = await (Q.purchase_orders_minimal().with_id_is(saved.id).limit(1)
                         .comment("Load a deliberately incomplete Checker control")
                         .purpose("Verify direct generated NotLoaded validation retains entity identity")
                         .execute_for_one(context))
        partial.update_contact_phone("5550101")
        before = counts.copy()
        try:
            await partial.audit_as("Reject mutation of a partial Checker control").save(context)
        except CheckException as error:
            assert counts == before
            clean()
            assert error.violations[0].rule_id == "invalid_type"
            assert error.violations[0].entity_type == "PurchaseOrder"
            observations.append({"round": round_number, "case": "partial_owner",
                                 "expectedEntityType": "PurchaseOrder", "zeroSQLiteIO": True,
                                 "wires": {p.value: error.violations[0].to_wire(p) for p in JsonFieldNamingProfile}})
        else:
            raise AssertionError("Modified partial owner was not rejected")

        # A customer Checker is allowed to declare a specialized child type and
        # retain an exact submitted alias pointer. This normal graph save must
        # neither replace that type with PurchaseOrder nor rename the pointer.
        original_registry = context.require_resource("checker_registry")

        class AliasRegistry:
            def checker(self, entity):
                original = original_registry.checker(entity)
                if entity != "OrderItem":
                    return original

                class Checker:
                    def check_and_fix(self, ctx, record, location, results):
                        original.check_and_fix(ctx, record, location, results)
                        results.append(CheckResult("required", ObjectLocation().property("product_name"),
                                       entity_type="ReviewedItem",
                                       source_instance_path="/order_item_list/0/product~1name~0alias"))
                return Checker()

        parent, child = graph()
        context.with_checker_registry(AliasRegistry())
        before = counts.copy()
        try:
            await parent.audit_as("Reject the custom Checker alias control").save(context)
        except CheckException as error:
            assert counts == before
            clean()
            assert len(error.violations) == 1
            violation = error.violations[0]
            assert violation.entity_type == "ReviewedItem"
            assert violation.location.model_path == "order_item_list[0].product_name"
            wires = {p.value: violation.to_wire(p) for p in JsonFieldNamingProfile}
            assert all(wire["sourceInstancePath"] == "/order_item_list/0/product~1name~0alias" for wire in wires.values())
            observations.append({"round": round_number, "case": "specialized_child_alias",
                                 "expectedEntityType": "ReviewedItem", "zeroSQLiteIO": True, "wires": wires})
        else:
            raise AssertionError("Custom child Checker did not reject the save")
        finally:
            context.with_checker_registry(original_registry)

    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as physical:
        parent_count = physical.execute("SELECT COUNT(*) FROM purchase_order_data").fetchone()[0]
        child_count = physical.execute("SELECT COUNT(*) FROM order_item_data").fetchone()[0]
        assert parent_count == child_count == 2
    print("CHECKER_METADATA=" + json.dumps({
        "language": "python", "passed": not failures, "rounds": 2,
        "normalGeneratedSave": True, "sameContextAndDatabase": True,
        "invalidSaves": len(observations), "physicalParents": parent_count,
        "physicalChildren": child_count, "observations": observations,
        "metadataFailures": failures,
    }, default=str))
    assert not failures, failures


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    options = parser.parse_args()
    if options.database.exists():
        parser.error("Use a NEW database path; the example never deletes test data")
    asyncio.run(verify(options.database))
