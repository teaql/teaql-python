"""Read one dispatch note through the model's installed JSON naming profile."""

import asyncio
import json
from pathlib import Path
import sys

from E import E
from Q import Q
from models.dispatch_order import DispatchOrder
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.provider.sqlite import create_sqlite_service
from teaql.runtime import TeaQLNotLoadedError, UserContext
import teaql

REFERENCE = "DOCK-042"
NOTE = "Lift-gate pickup after 14:00"


async def main(database, profile, phase):
    service = create_sqlite_service(database)
    try:
        context = UserContext.new().install(GENERATED_RUNTIME_MODULE).insert_resource("dataService", service)
        context.disable_sql_log()
        await context.ensure_schema()
        if phase == "first":
            order = await Q.dispatch_orders().comment("Prepare the receiving order").purpose(
                "Set its loading instruction").new_entity(context)
            order.update_distribution_center(1).update_order_reference(REFERENCE).update_handling_note(NOTE)
            await order.audit_as("Register the dispatch at the receiving terminal").save(context)

        child = Q.dispatch_orders().with_order_reference_is(REFERENCE).limit(1).comment("Select the dispatch order")
        root = await Q.distribution_centers().with_id_is(1).select_dispatch_order_list_with(child).limit(1).comment(
            "Read the dispatch desk and its order").purpose("Check the complete loading instruction").execute_for_one(context)
        assert root is not None
        expression = E.distribution_center(root)
        assert expression.dock_name().eval() == "North Receiving Terminal"
        assert expression.dispatch_order_list().first().order_reference().eval() == REFERENCE
        assert expression.dispatch_order_list().first().handling_note().eval() == NOTE
        matches = await Q.dispatch_orders().with_order_reference_is(REFERENCE).limit(2).comment(
            "Read back the dispatch record").purpose("Check the typed JSON round trip").execute_for_list(context)
        assert len(matches) == 1 and (matches[0].id, matches[0].version) == (1, 1)
        payload = matches[0].to_json()
        decoded = E.dispatch_order(DispatchOrder.from_json(payload))
        assert decoded.order_reference().eval() == REFERENCE and decoded.handling_note().eval() == NOTE

        sparse = await Q.distribution_centers_minimal().with_id_is(1).select_dock_name().limit(1).comment(
            "Read the desk without its dispatch orders").purpose("Verify the modeled preload instruction").execute_for_one(context)
        assert sparse is not None and E.distribution_center(sparse).dock_name().eval() == expression.dock_name().eval()
        try:
            E.distribution_center(sparse).dispatch_order_list().first().order_reference().eval()
        except TeaQLNotLoadedError as error:
            wire, human = error.to_wire(), str(error)
        else:
            raise AssertionError("A dispatch order was returned without loading the list")
        print("DISPATCH_DOCUMENT_PROFILE=" + json.dumps(dict(
            profile=profile, phase=phase, reference=REFERENCE, handlingNote=NOTE, id=matches[0].id,
            version=matches[0].version, dock=expression.dock_name().eval(), document=json.loads(payload),
            diagnostic=wire, human=human, runtimeOrigin=str(Path(teaql.__file__).resolve()),
        )))
    finally:
        await service.close()


if __name__ == "__main__":
    if len(sys.argv) != 4 or sys.argv[3] not in {"first", "restart"}:
        raise SystemExit("Usage: main.py DATABASE PROFILE {first|restart}")
    asyncio.run(main(*sys.argv[1:]))
