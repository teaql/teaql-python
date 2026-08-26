# School Management example

This retained SQLite example is generated from `model.xml`. It verifies idempotent
root/constant bootstrap, the database `snake_case` boundary, Python entity member
names, and explicit forward-relation loading. Schema bootstrap is explicit and is
called twice to prove that it does not duplicate seed rows.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
python -m app.main
```

Expected result:

```text
PASS Python School Management: idempotent bootstrap, multi-word hydration, and forward relations
```
