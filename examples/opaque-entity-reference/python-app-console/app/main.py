"""Apply a quantity edit to the order line referenced by a trusted editor."""
import asyncio
from dataclasses import dataclass
from datetime import timedelta
import json
import os
from pathlib import Path

import Q as query_module
from E import E
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.provider.sqlite import create_sqlite_service
from teaql.runtime import AeadEntityReferenceCodec, EntityReferenceTokenError, UserContext

from Q import Q


@dataclass(frozen=True)
class Editor:
    actor: str
    merchant_id: int

    def purpose_for(self, order_id):
        return f"edit-order:{self.actor}:{self.merchant_id}:{order_id}"


async def load_item(context, item_id):
    return await (
        Q.order_items().with_id_is(item_id).limit(1)
        .comment("Load the identified order line and its version")
        .purpose("Check current order membership before applying an edit")
        .execute_for_one(context)
    )


async def amend(context, editor, allowed_editors, order, token, quantity):
    if editor not in allowed_editors:
        raise PermissionError("The editor cannot currently change this merchant's orders")
    claims = context.decode_entity_reference(token, "OrderItem", editor.purpose_for(order.id))
    line = await load_item(context, claims.id)
    if line is None or E.order_item(line).sales_order_id().eval() != order.id:
        raise PermissionError("The line is outside the order being edited")
    if E.order_item(line).version().eval() != claims.version:
        raise ValueError("The edit page is stale")
    line.update_quantity(quantity)
    await line.audit_as("Accept an authorized quantity edit").save(context)


async def main():
    # The portable vector is checked separately. This workspace uses random nonces
    # and a synthetic key dedicated to its disposable order database.
    codec = AeadEntityReferenceCodec(1, {1: bytes([0x27]) * 32})
    provider = create_sqlite_service(os.environ["TEAQL_DATABASE_CONNECTION_STRING"])
    context = (
        UserContext.new().install(GENERATED_RUNTIME_MODULE)
        .insert_resource("dataService", provider)
        .with_entity_reference_codec(codec)
    )
    generated_library = Path(__file__).resolve().parents[2] / "python-lib-core"
    assert Path(query_module.__file__).resolve() == generated_library / "Q.py"
    await context.ensure_schema()
    merchant = await (
        Q.merchants_minimal().with_id_is(1).limit(1)
        .comment("Read the merchant installed by the domain model")
        .purpose("Open the order editor for this merchant")
        .execute_for_one(context)
    )
    assert merchant is not None
    editor = Editor("clerk", merchant.id)
    colleague = Editor("supervisor", merchant.id)
    allowed_editors = {editor, colleague}
    round_id = os.environ["TEAQL_SHOWCASE_ROUND"]
    order_number = f"EDIT-042-{round_id}"
    order = await (
        Q.sales_orders().comment("Prepare the order used by the editing page")
        .purpose("Create a real order under the trusted merchant").new_entity(context)
    )
    order.update_merchant(merchant.id).update_order_number(order_number)
    await order.audit_as("Open the merchant order").save(context)
    line = await (
        Q.order_items().comment("Prepare the item displayed on the order page")
        .purpose("Give the order an editable quantity").new_entity(context)
    )
    line.update_sales_order(order.id).update_sku("TEA-001").update_quantity(2)
    await line.audit_as("Record the initial tea quantity").save(context)

    stored = await load_item(context, line.id)
    assert stored is not None and E.order_item(stored).sales_order_id().eval() == order.id
    version = E.order_item(stored).version().eval()
    assert version == 1
    purpose = editor.purpose_for(order.id)
    token = context.encode_entity_reference("OrderItem", stored.id, version, purpose, timedelta(minutes=15))
    claims = context.decode_entity_reference(token, "OrderItem", purpose)
    assert token.startswith("tqr1.") and (claims.id, claims.version) == (stored.id, 1)

    midpoint = len(token) // 2
    tampered = token[:midpoint] + ("A" if token[midpoint] != "A" else "B") + token[midpoint + 1:]
    for candidate, wrong_purpose in [
        (tampered, purpose),
        (token, colleague.purpose_for(order.id)),
        (token, purpose.replace("edit-order", "view-order", 1)),
        (token, editor.purpose_for(order.id + 1)),
        (token, Editor(editor.actor, editor.merchant_id + 1).purpose_for(order.id)),
    ]:
        try:
            context.decode_entity_reference(candidate, "OrderItem", wrong_purpose)
        except EntityReferenceTokenError as error:
            assert error.code == "ENTITY_REFERENCE_INVALID"
        else:
            raise AssertionError("A tampered or out-of-scope reference was accepted")

    allowed_editors.remove(editor)
    try:
        await amend(context, editor, allowed_editors, order, token, 99)
    except PermissionError:
        pass
    else:
        raise AssertionError("A previously issued reference bypassed current authorization")
    allowed_editors.add(editor)
    await amend(context, editor, allowed_editors, order, token, 4)
    try:
        await amend(context, editor, allowed_editors, order, token, 99)
    except ValueError as error:
        assert str(error) == "The edit page is stale"
    else:
        raise AssertionError("The original reference accepted a second edit")

    updated = await load_item(context, line.id)
    assert updated is not None
    expression = E.order_item(updated)
    assert (expression.sales_order_id().eval(), expression.quantity().eval(), expression.version().eval()) == (order.id, 4, 2)
    print("ORDER_REFERENCE=" + json.dumps(dict(
        round=round_id, orderId=order.id, orderNumber=order_number, lineId=line.id,
        sku=expression.sku().eval(), version=2, quantity=4, denialCount=7)))


if __name__ == "__main__":
    asyncio.run(main())
