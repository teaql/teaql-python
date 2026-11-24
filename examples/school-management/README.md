# School startup and query showcase

The domain model `model.xml` owns both generated scopes: `python-lib-core` and
`python-app-console`. The workspace retains the original audited School create,
Q/E, constant reconciliation and SQL-intent assertions. Current scope identities
are recorded in `showcase.json`; the old root generated-files snapshot is
historical provenance. Run `bash verify.sh` from this scene for the focused
gate, including concurrent bootstrap, SQL-intent, two starts per logging mode,
and an independent SQLite result check. The main smoke application requires a
fresh database and rejects an existing file without deleting or changing it.

This retained SQLite example is generated from `model.xml`. It verifies generated
audited bootstrap mutation:
fixed root/constants, no-op repeated bootstrap, preservation of deployment-owned
root fields, reconciliation of drifted model-owned constants, and normal Q/E and
mutation behavior.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ../../..
export PYTHONPATH="../python-lib-core${PYTHONPATH:+:$PYTHONPATH}"
python -m app.main
```

Expected result:

```text
PASS Python School Management: bootstrap, portable Query parity, and forward relations
```

Run these commands from `examples/school-management/python-app-console`. The editable dependency supplies
the runtime from this checkout. The Python path supplies the generated domain library.
New entities use the awaited, Context-bound Q factory.

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
