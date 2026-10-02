# trace-chain-service application instructions

Implement only application-owned code. Generated models, requests, expressions,
Q, E and Runtime Module are read-only. Do not read or search generated library
source for API discovery, including verification-only discovery.

Use current model-aware Assist for the next operation, not every operation:

```text
cargo teaql --input model.xml python-assist-query/ksml_entity
cargo teaql --input model.xml python-assist-query/ksml_entity.ksml_field
cargo teaql --input model.xml python-assist-create/ksml_entity
cargo teaql --input model.xml python-assist-update/ksml_entity
cargo teaql --input model.xml python-assist-delete/ksml_entity
cargo teaql --input model.xml python-assist-expression/ksml_entity
```

Use actual KSML snake_case entity/field names and the actual model path. If
Assist cannot supply the required operation, report MISSING_ASSIST; do not guess
or open generated source. Compiler diagnostics and executable tests validate usage.

Every query is bounded and has non-blank comment and purpose. Use generated Q
for loading and E for loaded traversal. Load all scalar fields before mutation;
mark_for_deletion() and save(context) the composed graph with a non-blank audit_as
reason. Child reasons remain local; unannotated children inherit their parent.
Public execution accepts only UserContext. Schema changes are explicit through
context.ensure_schema(), with generated bootstrap intact.

Verify twice on one SQLite file without database cleanup. Use unique test labels,
keep generated library hashes unchanged, and retain commands, exit statuses and
skipped/unverified checks. Local source tests do not prove a published artifact.