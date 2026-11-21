# supplier-onboarding-service application instructions

## TeaQL workspace rules

- Work in application-owned files. Keep the generated domain library read-only.
- Discover API names and signatures through model-aware Assist only.
  Do not read or search generated library source for API discovery. Use the
  original evaluated KSML file or directory and its exact entity and field names.
- Ask for the current entity and action first. Request field-level query help
  only for the fields you use. If Assist lacks the operation, report
  `MISSING_ASSIST` with the entity, action, and relevant field or diagnostic.

```text
cargo teaql --input [model] python-assist-[action]/[entity]
cargo teaql --input [model] python-assist-query/[entity].[field]
```

Replace the bracketed values with the actual model path, action, entity, and
field. Actions include `query`, `list-page`, `create`, `update`, `delete`, and
`expression`. Validate API usage by compiling and testing the application.

- Use the trusted `UserContext` as the only runtime argument for generated query
  execution and saves. Resolve tenant, actor, authorization, and provider
  resources from trusted application setup.
- Keep queries bounded and provide a non-empty purpose and comment. Supply a
  non-empty audit reason for writes through the API shown by Assist.

## Application entry and context

Start in `app/main.py`. Use `create_context()` to install the generated
Runtime Module and configure the provider before calling `context.ensure_schema()`.

Every query is bounded and has non-blank comment and purpose. Use generated Q
for loading and E for loaded traversal. Load all scalar fields before mutation;
mark_for_deletion() and save(context) the composed graph with a non-blank audit_as
reason. Child reasons remain local; unannotated children inherit their parent.
Public execution accepts only UserContext. Schema changes are explicit through
context.ensure_schema(), with generated bootstrap intact.

Verify twice on one SQLite file without database cleanup. Use unique test labels,
keep generated library hashes unchanged, and retain commands, exit statuses and
skipped/unverified checks. Local source tests do not prove a published artifact.

## Optional standard telemetry

See [STANDARD_TELEMETRY.md](STANDARD_TELEMETRY.md) for the selected runtime's optional module, trusted activation variables and safe startup diagnostics.
