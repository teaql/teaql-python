# School Management example

This retained SQLite example is generated from `model.xml`. It verifies the Python runtime boundary for database `snake_case` columns, Python entity member names, and explicit forward-relation loading.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
python -m app.main
```

Expected result:

```text
PASS Python School Management: multi-word hydration and forward relations
```
