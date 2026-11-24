# Tenant purchase orders and supplier-line visibility

The procurement screen lists open purchase orders and supplier-owned lines.
Two tenants share the dispatch database. A partner handoff line is linked to
the Cedar order but belongs to Harbor. The Context policy scopes both the
order and the item query, so Cedar sees its own line and Harbor sees its own
order. Both callers reuse the same generated request and keep its original
open-order filter. A caller without procurement access is denied.

`model.xml` defines the tenants, orders and partner lines. The generated
`python-app-console` uses the immutable `python-lib-core` with a trusted
request policy on each Context. The verifier runs twice against the same
SQLite store and preserves the original shared-query calibration. That
calibration verifies shared nested-query identity and callback counts.

Run it from the repository root:

```bash
bash examples/query-policy/verify.sh
```
