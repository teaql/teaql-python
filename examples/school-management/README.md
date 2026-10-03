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

## Generated bootstrap Trace Chain gate

`bash scripts/verify-school-bootstrap-example.sh` (from the runtime root) runs
the actual generated School bootstrap twice per retained SQLite file, with SQL
logs on/off. No trace nodes are injected. It checks request intent, canonical
physical paths, matching typed mutation/audit lineage, caller identity
restoration, no-op reseeding and an audited constant edit/reconciliation. An
independent read-only connection must see the expected version at audit
delivery. Generated-library hashes must stay unchanged. The script uses local
runtime source and disables bytecode writes; all evidence and databases remain
available at the printed path.
