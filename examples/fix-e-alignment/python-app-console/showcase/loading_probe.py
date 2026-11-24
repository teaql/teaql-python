"""Generated Q/E regression for filtered forward details and mutation loading."""
import json


async def verify_loading(context, order_id):
    from E import E
    from Q import Q
    from teaql.runtime import CheckException, TeaQLNotLoadedError

    filtered = await (
        Q.purchase_orders().with_id_is(order_id)
        .select_tenant_with(Q.tenants_minimal().with_id_is(2).limit(1)
                            .comment("Load only a different tenant's detail"))
        .limit(1).comment("Keep the selected FK when detail filtering misses")
        .purpose("Verify Value / Null / NotLoaded and untouched partial associations")
        .execute_for_one(context)
    )
    assert E.purchase_order(filtered).tenant_id().eval() == 1
    try:
        E.purchase_order(filtered).tenant().name().eval()
    except TeaQLNotLoadedError as error:
        detail = error.to_wire()
        assert detail["code"] == "NOT_LOADED"
        assert detail["attemptedInstancePath"] == "/tenant/name"
        assert detail["expressionWithBrokenPoint"].count("<broken>") == 1
    else:
        raise AssertionError("A filtered-out target is NotLoaded, not loaded null")

    # The owner is complete; an untouched partial target must not block its save.
    filtered.update_contact_phone("5550102")
    await filtered.audit_as("Change only the complete owner's phone").save(context)
    persisted = await (
        Q.purchase_orders().with_id_is(order_id).limit(1)
        .comment("Reload the complete owner's successful update")
        .purpose("Verify a missing target detail did not block owner mutation")
        .execute_for_one(context)
    )
    assert E.purchase_order(persisted).contact_phone().eval() == "5550102"
    version = E.purchase_order(persisted).version().eval()

    partial = await (
        Q.purchase_orders_minimal().with_id_is(order_id).limit(1)
        .comment("Load only the identity and optimistic version")
        .purpose("Reject mutation of an incomplete owner before persistence")
        .execute_for_one(context)
    )
    partial.update_contact_phone("5550103")
    try:
        await partial.audit_as("Attempt to change an incomplete owner").save(context)
    except CheckException as error:
        assert any(result.rule_id == "invalid_type" and result.location.segments
                   for result in error.violations), error
    else:
        raise AssertionError("A modified partial owner must be rejected")
    unchanged = await (
        Q.purchase_orders().with_id_is(order_id).limit(1)
        .comment("Reload after the rejected incomplete mutation")
        .purpose("Verify both persisted values and optimistic version are unchanged")
        .execute_for_one(context)
    )
    assert E.purchase_order(unchanged).contact_phone().eval() == "5550102"
    assert E.purchase_order(unchanged).version().eval() == version
    print("CORE_LOAD_EXAMPLE=" + json.dumps({
        "language": "python", "passed": True, "foreignKeyPreserved": True,
        "filteredDetailNotLoaded": detail, "untouchedPartialTargetSave": True,
        "modifiedPartialOwnerRejected": True, "rejectedVersionUnchanged": True,
    }))
