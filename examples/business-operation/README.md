# Business operation: inventory shipping

`BusinessOperation` groups independent entity graph saves into a single Python
runtime transaction. The provider qualified here is **file SQLite**.

Run from the repository using its installed dependencies:

```bash
PYTHONPATH=src python examples/business-operation/warehouse.py
python -m pytest tests/runtime/test_business_operation.py -q
```

`BusinessOperation` is a trusted server registration containing a complete typed
scalar input schema, authorization, preparation, handler, and invariant validator.
Every input field enters a versioned fingerprint. The validator runs even when
the handler forgets to enforce the reviewed domain contract. Review and protect
these registrations like application policy; the runtime cannot infer missing
business rules or defend against arbitrary code with raw database credentials.

The handler receives an explicit operation context. Native graph saves and
existing generated entity `.save(context)` calls made through that context join
one database transaction. Ordinary independent saves keep their existing separate
transaction boundaries. Context supplies services, not a shared mutation ledger.
Each graph retains its Checker, Fix, mutation policy, trace, rollback and commit
callbacks. A caught graph error marks the whole operation rollback-only.

The shipping handler changes stock and order through native TeaQL graph APIs.
It contains no transaction or idempotency protocol. A reviewed postcondition
requires exact inventory/order deltas and the correct returned business result.
The acceptance suite also uses real generated `WorkItem.save()` calls to verify
that the coordinator works with existing generated entities without patching
their source.

At explicit startup, call `ensure_schema()` for domain metadata, then
`service.ensure_business_operation_schema()` for replay and committed-operation
audit tables. No DDL runs implicitly during a business operation. SQLite
`BEGIN IMMEDIATE` protects the complete read/decision/write interval across
processes. This trades write concurrency for a small, testable initial guarantee;
MySQL and PostgreSQL transactions alone are not automatically qualified.

Successful business effects, replay snapshot and operation audit commit together.
An identical key and parameters return the original JSON result even after other
operations change the order. Different business parameters or operation version
with that key conflict. Keys are scoped by trusted active-root identity and
operation name. Authorization runs again before replay. No keys expire in v1;
retention/compaction, quotas and encryption policy remain production work.

External audit sinks remain post-commit delivery. Sink failure is reported as
`GraphCommittedError(committed=True)`; the durable operation-audit row still
exists. Automatic outbox delivery and external side effects are outside this
minimal implementation. A commit exception is conservatively
`OPERATION_COMMIT_UNKNOWN`, never a claim of rollback; recover with the original
key and newly loaded state. Other failures retain their cause and report
`rolled_back` only if rollback succeeded. There is no automatic handler retry.

Supported input fields are exactly `str`, `int`, and `bool`; missing/extra fields
and Python `bool` where `int` is required are rejected. Complex objects,
normalization and nullable input schemas require a separately reviewed extension.
Results must be JSON-serializable. Use one task per operation context; parallel
or escaped context use, nested operations and provider replacement are rejected.

This example covers shipping, not complete transfer creation/receive/cancel.
Full schema-level inventory constraints, operation registry governance, arbitrary
provider routing, other databases, retention, and full harness/Assist rollout
remain outside its qualified scope. Strict independent delivery checks remain
necessary.
