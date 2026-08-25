# Python runtime conformance example

This retained SQLite example is generated from `model.xml` and verifies the minimum runtime-owned contract: explicit `ensure_schema`, Create, Update, Delete, typed Q/SmartList, E loaded/null/not-loaded semantics, and Checker rejection before persistence.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
python -m app.main
```

Regenerate it with the local code generator's `python-app-console` target before checking a new generator/runtime combination.
