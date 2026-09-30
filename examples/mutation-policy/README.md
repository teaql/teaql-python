# Mutation Policy example

This focused example installs an application-owned policy and exact approval
through `UserContext`, preflights an entire two-entity graph after Checker/Fix,
and proves that a denied graph reaches no persistent provider mutation. The
successful audit events retain the same governance snapshot.

Run it against the local runtime under development:

```bash
PYTHONPATH=src python examples/mutation-policy/main.py
```

The deterministic in-memory transaction keeps the example independent of a
database. Built-in SQL and TFP providers exercise the same policy boundary in
their focused runtime tests.
