# TeaQL Python

Review the business operation, not pages of persistence plumbing.

TeaQL Python is a reusable, domain-independent runtime for model-aware applications.
A generated domain library gives your application language-native **Q** queries,
**E** expressions and governed graph mutations. The runtime executes them
through metadata, Context, Checker, Policy and provider boundaries.

The goal is to let people and coding agents express—and review—business intent
in a small amount of application code.

## What you gain

| Capability | Benefit to application developers |
| --- | --- |
| Composable Q API | Combine filters, projections and relation requests without duplicating relationship-loading code; review what is being requested. |
| Safe E API | Distinguish an unloaded field from a loaded NULL; do not mistake an incomplete result for a business fact. |
| Governed graph Save | Stage creates, updates and deletions, then validate and persist through one Save boundary rather than hand-written SQL loops. |
| Execution and audit evidence | Follow declared intent, SQL routes and mutation responsibility when debugging or explaining a change. |

## Try it with your coding agent

You can start with an agent you already use. Paste this prompt:

```text
Follow the current instructions at https://github.com/teaql/teaql-agent-kit.
Build a small school-management application in Python using SQLite.
Evaluate and repair the model, generate the library and workspace, then verify
Q, E, Checker and audited Save. Report commands, results and remaining frictions.
```

The [Agent Kit](https://github.com/teaql/teaql-agent-kit) guides modeling,
evaluation/repair, generation and application customization. It may install
toolchains and download dependencies; review installation permissions and the
final execution report. It is a workflow, not a guarantee of unattended correctness.

## Run the local example

Python 3.10+; Python 3.12+ is recommended. Async SQL execution uses the selected provider driver. From a checkout of this repository:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
export PYTHONPATH="$PWD/src"
(cd examples/school-management && python -m app.main)
```

The [School example](examples/school-management/README.md)
exercises SQLite schema/bootstrap and generated application APIs against this
repository's local runtime. No external database server or generator is needed
to run the retained generated example. Use only the example's test database;
reset/repeated-run behavior is documented in its README.

## Query and read the result

These application-code excerpts assume the example's generated imports, trusted
Context and an existing object identity. `Q` and `E` belong to the generated
domain library, not a generic runtime object with arbitrary field strings.
See the [application source](examples/school-management/app/main.py) for complete setup.

```python
school = await (
    Q.schools().with_id_is(school_id)
    .select_platform_with(Q.platforms_minimal().select_name().select_base_url())
    .select_school_type_with(Q.school_types_minimal().select_name().select_code())
    .comment("what: load the school and its reference data")
    .purpose("why: review a school before editing")
    .execute_for_one(context)
)
if school is None:
    raise ValueError("School not found")
```

The selected relation request is another typed query: it can be composed and
reused independently. `comment` describes **what**; `purpose` describes **why**.
Both must be non-empty, even when logging is disabled.

```python
type_code = E.school(school).school_type().code().eval()
```

E reads the loaded graph without implicitly querying the database. Unloaded
modeled fields remain guarded, rather than silently becoming NULL. The exact
error/result representation follows the language's API. A NULL fallback is
not permission to ignore an unloaded property.

## Change the object and save

Load the complete scalar fields of every persisted object you actually modify.
A display-only partial projection is not a complete mutation input. Unmodified
reference objects do not have to become fully loaded just to save their parent.

```python
school.update_name("Riverside Academy")
await school.audit_as("Rename the reviewed school").save(context)
```

Save traverses the reached mutation graph, runs Checker/Fix and the configured
customer Mutation Policy, then uses the provider transaction boundary.
An explicit policy denial blocks persistence. Missing customer policy or exact
approval emits a warning; it is not automatic rejection. Marking for deletion
stages a change—the audited Save performs it. Atomicity is provider/route scoped,
not a distributed transaction across unrelated databases.

## See why an operation happened

Query and Mutation diagnostic logs are enabled by default and can be switched
off independently. Logging off does not disable intent validation or Policy.

Intent, physical SQL paths and mutation responsibility are separate facts.
For example, a safe diagnostic can tell an operator which query populated a
screen, and an audit can explain why a saved object changed.

Illustrative, shortened view—not a literal logger format or a benchmark result:

```text
query entity=School comment="load the reviewed object" purpose="edit form" outcome=success
SQL: SELECT id, version FROM school_data WHERE id = 42;
trace: School -> request -> sqlite -> select
mutation entity=School auditReason="Rename the reviewed school" outcome=committed
lineage: School#42("Rename the reviewed school")
```

SQL execution stays parameterized. Diagnostic SQL has parameters substituted
after field-aware masking; it is not a question-mark template you must manually
reconstruct. Ordinary bindings stay visible, sensitive bindings use the shared
mask algorithm, and credentials/unknown bindings stay hidden. A masked statement
is labeled `MASKED; NOT REPLAYABLE`; SQL that cannot be safely rendered is omitted.
Application mutation audits are delivered after commit and discarded on rollback.
This is not a durable audit outbox. Do not put secrets in comment or purpose.

## Use the published runtime

Current documented runtime: **0.3.0**. Keep domain-library and runtime
versions compatible; regenerate older libraries when their provider or graph
adapter SPI has changed.

```bash
python -m pip install teaql==0.3.0
```

Generation is a separate service; see the [Agent Kit](https://github.com/teaql/teaql-agent-kit)
for producing the application-specific library and workspace. Repository examples
use local source; isolated released-package regression is a separate gate.

## Supported scope

Python provides asynchronous local SQL execution and a TFP client, not a public TFP server endpoint. Generated classes and expressions expose model-aware APIs; Python annotations are not a Rust-style compile-time guarantee. Provider and advanced-feature coverage is tracked explicitly in conformance.

One semantic model can produce language-native applications across
[Java](https://github.com/teaql/teaql-java),
[Rust](https://github.com/teaql/teaql-rs),
[TypeScript](https://github.com/teaql/teaql-ts),
[Go](https://github.com/teaql/teaql-golang),
[Swift](https://github.com/teaql/teaql-swift),
[.NET](https://github.com/teaql/teaql-dotnet) and
[Python](https://github.com/teaql/teaql-python).
That does not imply identical APIs, providers or complete cross-language feature parity.
The semantic model defines business objects, fields, relationships and states;
it is not the language model used by a coding agent.
The [conformance matrices](https://github.com/teaql/teaql-conformance)
distinguish implemented source, executed examples, artifact verification and release.

## Verification and customization

```bash
python -m pip install -e '.[test]'
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q
PYTHONDONTWRITEBYTECODE=1 bash scripts/verify-examples.sh
```

The full example gate is the acceptance entry point for local runtime changes.
External-provider tests need their configured services; skips are not live-provider
evidence. A committed-operation error after audit delivery failure must not be
retried as if the business transaction rolled back.

Install application-owned policies, ID/business-ID services, logging sinks,
transports and other supported SPIs through trusted runtime/Context setup.
Request JSON is not allowed to replace those trusted capabilities.

- [Runtime guide: modules, SPI and advanced verification](RUNTIME_GUIDE.md)
- [Modules and providers](RUNTIME_GUIDE.md#3-available-modules)
- [Mutation Policy example](examples/mutation-policy)
- [Facet example](examples/facet-trace/README.md)
- [Opaque reference example](examples/opaque-entity-reference)

## Safe troubleshooting

Default diagnostics do not authorize plaintext sensitive data. Controlled
debugging requires the exact acknowledgement below and any sensitive sink
required by the runtime:

```bash
export TEAQL_ALLOW_SENSITIVE_PLAINTEXT_LOGS=I_UNDERSTAND_SENSITIVE_DATA_MAY_BE_WRITTEN_TO_DISK
```

Debug output is explicitly labeled. Credentials and unknown bindings remain
protected; the flag does not erase old files or govern application/driver
prints outside TeaQL. Restrict access and retention, then unset it and restart.
See the [runtime guide](RUNTIME_GUIDE.md) for log switches and extension details.
