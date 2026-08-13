# Order Management — Python + SQLite

This example is ready to run from a terminal. No model editing, generator installation, database server, or prebuilt database file is required.

```bash
cd examples/order-management
python3 -m venv .venv
.venv/bin/pip install -e python-lib-core
.venv/bin/python python-app-console/app.py
```

On the first run, TeaQL reports that `.local/order.db` is absent, creates it, ensures the schema from generated metadata, seeds deterministic data, queries it with `comment(...).purpose(...)`, and saves a preset with `audit_as(...)`. Run it again to see idempotent initialization.

## Read the code

- Start with `python-app-console/app.py`: this is handwritten application code.
- Then read `python-lib-core/Q.py` and `python-lib-core/requests/customer_order_request.py`: these are generated query APIs.
- Read `python-lib-core/models/customer_order.py`: this is the generated entity and audited save API.
- `python-lib-core/teaql/` is generated runtime support. Notice that `execute_for_list` accepts exactly one argument: the trusted `UserContext`; runtime resources are injected when that context is initialized.

The model used to generate the library is documented separately as provenance; it is not needed to run this example. Generated files should be regenerated, never edited by hand.

## Verify the first result

Expect `WEB-2026-001`, `2026-08-12`, and `129.95`, plus matching immutable and application-safe audit events. A second run must report that both the seed and preset already exist.

## Customize it

Change `with_order_number_containing`, ordering, or relation selection in `app.py`. Inspect the generated request for exact snake-case API names. Initialize new services and trusted global policy in `UserContext`; never add a second execute argument. Keep handwritten code in `python-app-console` and regenerate `python-lib-core`.
### Materialized-list hard limit

`execute_for_list` protects the service by applying a default hard limit of 10,000 rows. A requested page size above that ceiling fails explicitly. Trusted application code can call `hard_limit(...)` to override the outer-query ceiling. **Caution:** most applications should not override it; do so only for a reviewed, exceptional requirement. This setting does not describe streaming execution.

### Streaming large root queries

`execute_for_stream(ctx, chunk_size)` is an async iterator of generated entities:

```python
async for order in request.comment("export orders").purpose("reviewed export").execute_for_stream(ctx, 500):
    await write_order(order)
```

Breaking or closing the iterator releases the cursor. **Caution:** normally keep the default 1,000. Streaming relation or aggregate enhancement is rejected; use a root query or `execute_for_list`. The ordinary federation request/response protocol cannot carry local streaming configuration.

### Optional continuous browsing optimization

For a browse-only screen ordered by the unique `id`, trusted application code may opt in before `purpose(...)`:

```python
request = (Q.customer_orders()
    .order_by_id_descending()
    .offset(page * page_size)
    .limit(page_size)
    .optimize_for_continuous_page_fetch_with("recent-orders", 60))
orders = await request.purpose("browse recent orders").comment("order browser").execute_for_list(ctx)
```

The runtime remembers the previous boundary in a bounded, expiring cursor store owned by `UserContext`. A matching next page transparently uses an `id` seek instead of a deep offset; cache misses or unsupported query shapes retain correct offset semantics. The cursor ID and selected plan are observable for diagnosis.

**Caution:** this is an explicitly approximate optimization for continuous browsing, not business logic, reconciliation, export, or a stable snapshot. Prefer omitting an exact count on browse screens. The hint is local runtime state and is deliberately absent from federation JSON, so a remote caller cannot enable or alter it.
