# Supplier onboarding in 15 locales with TeaQL Python

The [KSML model](model.xml) describes a warehouse and its suppliers. The
[semantic model](semantics.json) supplies two registrations to the generated
console. One lacks a supplier name. The other sets the minimum order quantity
to 3, below the model's limit of 10. The app makes real audited saves against
SQLite and reads the supplier table back through generated Q.

## Run and select a locale

Use Python 3.10 or newer and install this checkout's Python dependencies from
the repository root with `python3 -m pip install -e .`. The runner uses the
TeaQL 0.6.0 source in this checkout and the sibling generated domain library.

```sh
bash examples/supplier-onboarding-i18n/run.sh
bash examples/supplier-onboarding-i18n/run.sh --locale fr
bash examples/supplier-onboarding-i18n/run.sh --all
bash examples/supplier-onboarding-i18n/run.sh --edge-cases
```

Output is UTF-8 JSON Lines. Look at `effectiveLocale`, `messageKey`,
`location`, `arguments`, and `message` on each validation row. `--all`
switches through all 15 locales in one process. Add `--repeat 2` to run the
same mode twice against one temporary database. `PYTHON` selects the Python
executable and defaults to `python3`. An empty `PYTHON` also uses that default.

The app uses `context.set_locale_code(code)` before validation and reads
`context.language().value`. With no selection a fresh context uses `en`.
`ZH_hant` normalizes to `zh-TW`. Both the empty string and an unknown code
raise `UnsupportedLocaleError` and leave the previous locale in place. Single
locale mode reports the rejection and exits 2. The example selects locale
only through the CLI and trusted context wiring. Business input and process
locale variables supply no locale configuration.

## How the message is produced

1. The generated model is installed on a `UserContext` with a SQLite provider.
   The setter parses and normalizes the requested locale before recording it.
2. The generated save checks the model. `CheckException.violations` contains
   the rule, canonical location and parameters. The example reports
   `checker.required` and `checker.min` with the source rule IDs alongside them.
3. The checker renderer chooses a template for the locale and location shape,
   then binds the field label and the applicable parameters, such as
   `{system}` for the lower bound. The generated presentation metadata
   supplies field names where available.
4. The example explicitly installs its generated application catalog with
   `I18nCatalog.from_dict(payload, I18nCatalog.builtin())`. That catalog lacks
   these Vietnamese message overrides, so the two rendered messages stay
   identical to the built-in Vietnamese results. The legacy catalog's
   `message` method tries application and built-in entries in the selected
   locale, then application and built-in English, then returns the key.
   The natural checker renderer also supports per-shape templates and
   generic `checker.invalid` when the rule has no natural template.

The independent context stays French while the main context changes from
Japanese to Arabic and back. The sample's localized sentence templates can
include English domain labels when no translated label is present.
[Context source](../../src/teaql/runtime/context.py) · [Locale and catalog source](../../src/teaql/runtime/i18n.py) · [Checker rendering source](../../src/teaql/runtime/checker_messages.py)

## Run the same scene in another runtime

Use the corresponding example in a sibling checkout. Keep the KSML,
semantic input, rule keys and field paths. Follow the other example's build
and context wiring for its host language.

[Java](../../../java/examples/supplier-onboarding-i18n/) ·
[Rust](../../../rust/examples/supplier-onboarding-i18n/) ·
[TypeScript](../../../typescript/examples/supplier-onboarding-i18n/) ·
[Go](../../../go/examples/supplier-onboarding-i18n/) ·
[Python](./) ·
[C#/.NET](../../../dotnet/examples/supplier-onboarding-i18n/) ·
[Swift](../../../swift/Examples/SupplierOnboardingI18n/)

## Add a locale

For a new runtime locale such as Italian, register `ITALIAN = "it"` in
`Locale` in `src/teaql/runtime/i18n.py` and add aliases in `_ALIASES` as
needed. Extend the legacy and natural built-ins and the per-locale checker
presentation defaults used in `checker_messages.py`. The legacy entry keeps
the key and placeholder.

```json
{
  "it": {
    "messages": {"checker.required": "Il campo {location} è obbligatorio"},
    "vocabulary": {}
  }
}
```

For natural checker messages supply the appropriate `one`, `two` and
`deep` templates in `src/teaql/runtime/natural-messages-v1.json`, preserving
placeholders such as `{field}` and `{system}`. Update the shared locale model
and generator locale list before regenerating the examples. Verify alias
selection, both real saves and missing-translation fallback, plus the
separation of locale state between contexts. For overrides of an already
supported locale, explicitly attach the application catalog instead.
