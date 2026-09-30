# Query Policy example

This source-based example proves that a context-owned Query Policy receives an
independent query graph, governs root and nested queries once, preserves shared
nested-query identity, leaves the caller request reusable, and fails closed on
denial.

Run it from the repository root:

```bash
PYTHONPATH=src python examples/query-policy/main.py
```
