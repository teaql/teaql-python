# customer-onboarding-service Python console

From this workspace, run `PYTHONPATH=../python-lib-core python -m app.main` with the TeaQL runtime installed.
Installing the generated Runtime Module is passive;
schema reconciliation remains an explicit application action.
The console main() explicitly awaits `context.ensure_schema()` after `create_context()`
and before reporting readiness. Importing the console or calling `create_context()`
does not reconcile schema.


## Optional standard telemetry

See [STANDARD_TELEMETRY.md](STANDARD_TELEMETRY.md) for the selected runtime's optional module, trusted activation variables and safe startup diagnostics.
