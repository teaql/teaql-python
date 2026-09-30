# Opaque entity reference

This example proves that Python emits the same portable `tqr1` golden vector as
Go and .NET, decodes it through `UserContext`, and rejects purpose
substitution. Decoding authenticates identity claims; it does not replace the
application's ownership, permission, or optimistic-version checks.
