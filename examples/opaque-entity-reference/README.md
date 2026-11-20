# Edit an order using an opaque line reference

The [order editing model](model.xml) defines the merchant, sales order and
line. The Python console workspace uses that generated domain library, a
Context-installed reference codec, and an application-owned editor policy.
It checks actor, merchant, order and purpose binding before changing the
line quantity. Revoked permission and stale versions also reject the edit.

```bash
bash examples/opaque-entity-reference/verify.sh
```

## Portable vector calibration

This example proves that Python emits the same portable `tqr1` golden vector as
Go and .NET, decodes it through `UserContext`, and rejects purpose
substitution. Decoding authenticates identity claims; it does not replace the
application's ownership, permission, or optimistic-version checks.
