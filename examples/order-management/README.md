# Order Management — Python + SQLite

This example is ready to run from a terminal. No model editing, generator installation, database server, or prebuilt database file is required.

```bash
cd examples/order-management
python3 -m venv .venv
.venv/bin/pip install -e ../..
.venv/bin/python python-app-console/app.py
```

On the first run, TeaQL reports that `.local/order.db` is absent, creates it, ensures the schema from generated metadata, seeds deterministic data, queries it with `comment(...).purpose(...)`, and saves a preset with `audit_as(...)`. Run it again to see idempotent initialization.

## Read the code

- Start with `python-app-console/app.py`: this is handwritten application code.
- `python-lib-core` contains generated Q/E/entity metadata, not an embedded runtime. Human maintainers may inspect it; AI API discovery should use model-aware Assist instead.
- This example explicitly installs the local runtime from the repository root. `execute_for_list` accepts exactly one argument: the trusted `UserContext`; runtime resources are injected when that context is initialized.
- Creation uses `await Q...comment(...).purpose(...).new_entity(context)` before the generated updater methods and audited save. The ID already exists before save; constructors and JSON hydration are not creation APIs.

The model used to generate the library is documented separately as provenance; it is not needed to run this example. Generated files should be regenerated, never edited by hand.

## Verify the first result

Expect `WEB-2026-001`, `2026-08-12`, and `129.95`, plus matching immutable and application-safe audit events. A second run must report that both the seed and preset already exist.

## Customize it

Change `with_order_number_containing`, ordering, or relation selection in `app.py`.
Discover exact APIs through `cargo teaql --input model.xml python-assist-query/customer_order`
and field-specific Assist when needed. Initialize new services and trusted global
policy in `UserContext`; never add a second execute argument. Keep handwritten
code in `python-app-console` and regenerate only `python-lib-core`.
### Materialized-list hard limit

`execute_for_list` protects the service by applying a default hard limit of 10,000 rows. A requested page size above that ceiling fails explicitly. Trusted application code can call `hard_limit(...)` to override the outer-query ceiling. **Caution:** most applications should not override it; do so only for a reviewed, exceptional requirement. This setting does not describe streaming execution.

### Streaming large root queries

`execute_for_stream(ctx, chunk_size)` is an async iterator of generated entities:

```python
async for order in request.comment("export orders").purpose("reviewed export").execute_for_stream(ctx, 500):
    await write_order(order)
```

Breaking or closing the iterator releases the cursor. **Caution:** normally keep the default 1,000. Streaming relation or aggregate enhancement is rejected; use a root query or `execute_for_list`. The ordinary federation request/response protocol cannot carry local streaming configuration.
