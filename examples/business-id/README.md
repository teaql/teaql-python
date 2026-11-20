# Number two purchase orders

The procurement platform records orders from Northwind and Contoso. The
trusted Context supplies the business day, the deterministic example key and
the SQLite allocator. The model configures the `ORD` prefix and a six-character
Base36 suffix. Create and read the orders through the generated API.

- `model.xml` models the platform and the numbered purchase order.
- `python-lib-core/` is the generated domain library.
- `python-app-console/app/main.py` is the console entry.
- `python-app-console/calibration/` retains the original allocator and retry assertions.

The console saves both purchase orders, retries the first save, and reads both
back by their typed numbers. It rejects a missing audit reason and checks that
the unaudited order never appears. The SDK's `scripts/verify-examples.sh`
runs both the workspace and the allocator calibration. The focused Conformance
gate also runs twice on the same SQLite file and checks its stored rows.
