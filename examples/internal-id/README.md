# Warehouse purchase orders with Context-assigned IDs

Riverside Distribution Center checks the identities on its incoming purchase
orders and their items. The warehouse model lives in `model.xml`. Its generated
domain code is kept in `python-lib-core` and executed from `python-app-console`.

The application installs an allocator with `with_internal_id_allocator` and keeps the
SQLite provider responsible for persistence. Direct and batch orders receive
IDs 100–102. An explicit order at 500 advances the order floor. The next
graph uses order 501 and item IDs 200 and 201 from a separate sequence.
An injected allocator failure writes no pending order or item. Retrying
with the same reserved parent then commits both linked items in one save.

From the runtime repository, run `bash examples/internal-id/verify.sh`.
Both launches read the same SQLite database. The restart checks the persisted
graph and the manually assembled School calibration runs separately.
The example allocator is in-memory and the restart only reads the existing
rows. Shared production allocation requires durable, atomic floor reservation.
