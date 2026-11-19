"""Native generated mutation ownership: independent new objects and list rows."""
import json


async def verify_ownership(context):
    from E import E
    from Q import Q

    async def all_rows(comment):
        return await (Q.purchase_orders().limit(20).comment(comment)
                      .purpose("Verify independently saveable roots never share pending mutations")
                      .execute_for_list(context))

    before = await all_rows("Inspect the bounded initial ownership fixture")
    first = ((await Q.purchase_orders().comment("Prepare independent owner A")
             .purpose("Verify Context does not own mutation ledgers").new_entity(context)))
    second = ((await Q.purchase_orders().comment("Prepare independent owner B")
              .purpose("Verify Context does not own mutation ledgers").new_entity(context)))
    first.update_contact_phone("5550300").update_internal_note(None)
    second.update_contact_phone("5550400").update_internal_note(None)
    saved_a = await first.audit_as("Save only independent new owner A").save(context)
    assert len(await all_rows("Inspect A's save before saving B")) == len(before) + 1
    saved_b = await second.audit_as("Explicitly save independent new owner B").save(context)
    batch = await all_rows("Load independently saveable owners in one batch")
    assert len(batch) == len(before) + 2
    owner_a = next(row for row in batch if row.id == saved_a.id)
    owner_b = next(row for row in batch if row.id == saved_b.id)
    owner_a.update_contact_phone("5550301")
    owner_b.update_contact_phone("5550401")
    await owner_a.audit_as("Save only A from a multi-root result").save(context)
    unchanged = await (Q.purchase_orders().with_id_is(saved_b.id).limit(1)
                       .comment("Inspect B after saving A")
                       .purpose("Verify saving A neither persists nor commits B").execute_for_one(context))
    assert E.purchase_order(unchanged).contact_phone().eval() == "5550400", "A persisted B's pending mutation"
    assert E.purchase_order(unchanged).version().eval() == 1
    await owner_b.audit_as("Save B after A without discarding its pending mutation").save(context)
    changed = await (Q.purchase_orders().with_id_is(saved_b.id).limit(1)
                     .comment("Inspect the later independent B save")
                     .purpose("Verify B's mutation survives A's save").execute_for_one(context))
    assert E.purchase_order(changed).contact_phone().eval() == "5550401"
    assert E.purchase_order(changed).version().eval() == 2
    from paged_ownership import verify_page_stream
    await verify_page_stream(context, saved_a.id, saved_b.id)
    print("CORE_MUTATION_OWNERSHIP=" + json.dumps({
        "language": "python", "passed": True, "independentNewRoots": True,
        "batchRootIsolation": True, "siblingVersionUnchanged": True,
        "siblingPendingMutationRetained": True,
    }))
