# School Management example

This retained SQLite example is generated from `model.xml`. It verifies generated
audited bootstrap mutation:
fixed root/constants, no-op repeated bootstrap, preservation of deployment-owned
root fields, reconciliation of drifted model-owned constants, and normal Q/E and
mutation behavior.

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
