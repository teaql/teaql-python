"""Nonzero-offset page and cross-chunk scalar-stream deferred-save ownership."""
from contextlib import aclosing
import json


async def verify_page_stream(context, id_a, id_b):
    from E import E
    from Q import Q

    before = await (Q.purchase_orders().limit(20).comment("Inspect the page ownership fixture")
                    .purpose("Establish the bounded expected exact total").execute_for_list(context))
    sentinel = ((await Q.purchase_orders().comment("Prepare a page-offset sentinel")
                .purpose("Test a genuinely nonzero offset without excluding the tested owners").new_entity(context)))
    sentinel.update_contact_phone("5550500").update_internal_note(None)
    await sentinel.audit_as("Save the synthetic page sentinel").save(context)
    expected_total = len(before) + 1

    async def exercise(rows, label, previous_phone, next_phone, previous_version):
        owner_a = next(row for row in rows if row.id == id_a)
        owner_b = next(row for row in rows if row.id == id_b)
        owner_a.update_contact_phone("55503" + next_phone[-2:])
        owner_b.update_contact_phone(next_phone)
        # Reusing Context for another query must not change either ledger owner.
        await (Q.tenants_minimal().limit(1).comment("Run an unrelated query before deferred saves")
               .purpose("Verify deferred ownership survives Context reuse").execute_for_list(context))
        await owner_a.audit_as("Save only A from " + label).save(context)
        persisted = await (Q.purchase_orders().with_id_is(id_b).limit(1)
                           .comment("Inspect B after the deferred A save")
                           .purpose("Verify unrelated root values and version remain untouched").execute_for_one(context))
        assert E.purchase_order(persisted).contact_phone().eval() == previous_phone
        assert E.purchase_order(persisted).version().eval() == previous_version
        await owner_b.audit_as("Save B later from " + label).save(context)
        persisted = await (Q.purchase_orders().with_id_is(id_b).limit(1)
                           .comment("Inspect the later deferred B save")
                           .purpose("Verify pending B survived A's commit").execute_for_one(context))
        assert E.purchase_order(persisted).contact_phone().eval() == next_phone
        assert E.purchase_order(persisted).version().eval() == previous_version + 1

    page = await (Q.purchase_orders().order_by_id_descending().offset(1).limit(2).count()
                  .comment("Load a nonzero-offset page of independently saveable roots")
                  .purpose("Verify exact count and page mutation isolation").execute_for_list(context))
    assert len(page) == 2 and page.total_count == expected_total
    assert {row.id for row in page} == {id_a, id_b}
    await exercise(page, "a nonzero-offset page", "5550401", "5550402", 2)
    request = (Q.purchase_orders().order_by_id_ascending().limit(20)
               .comment("Stream independent roots across single-row chunks")
               .purpose("Verify cross-chunk deferred-save ownership"))
    async with aclosing(request.execute_for_stream(context, chunk_size=1)) as stream:
        rows = [row async for row in stream]
    assert len(rows) == expected_total
    await exercise(rows, "a fully consumed scalar stream", "5550402", "5550403", 3)
    print("CORE_MUTATION_PAGING=" + json.dumps({
        "language": "python", "passed": True, "pageOffset": 1, "pageSize": 2,
        "exactCount": expected_total, "pageRootIsolation": True, "deferredSaveAfterContextReuse": True,
        "streamProfile": "scalar-typed", "streamChunkSize": 1, "streamRootIsolation": True,
        "siblingPendingMutationRetained": True,
    }))
