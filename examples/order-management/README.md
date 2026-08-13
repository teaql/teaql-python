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
