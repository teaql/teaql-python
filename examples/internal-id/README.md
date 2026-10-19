# Context-owned Internal ID example

This SQLite example installs a typed, asynchronous `InternalIdAllocator` on
`UserContext`. Direct, nested-batch, and graph saves use the same allocator;
explicit IDs advance its floor. An allocator failure rejects the write rather
than silently falling back to the provider's ID space.

```bash
PYTHONPATH=src python examples/internal-id/main.py
```

The in-memory allocator here is for one-process demonstration only. Production
allocators shared by multiple processes must reserve IDs and explicit-ID floors
durably and atomically. Gaps after failed operations are acceptable; reuse is
not.
