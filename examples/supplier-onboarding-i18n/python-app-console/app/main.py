"""Run supplier registration through the generated Python workspace."""

import asyncio
import json
from pathlib import Path
import sys

from teaql.data_service import SQLiteTeaQLClient
from teaql.runtime import UserContext
from teaql.runtime.i18n import CheckException, I18nCatalog, UnsupportedLocaleError

from Q import Q
from runtime_module import GENERATED_RUNTIME_MODULE


def create_context(client):
    return UserContext.new().install(GENERATED_RUNTIME_MODULE).insert_resource("dataService", client)


def emit(step, context, event_type, **details):
    result = {"type": event_type, "context": step["context"],
              "effectiveLocale": context.language().value, **details}
    print("TEAQL_I18N_SHOWCASE " + json.dumps(result, ensure_ascii=False))


async def register_supplier(context, warehouse_id, values):
    supplier = (Q.suppliers().comment("Prepare supplier registration")
                .purpose("Register a supplier for warehouse purchasing").new_entity(context))
    supplier.update_warehouse(warehouse_id)
    supplier.update_name(values["name"])
    supplier.update_minimum_order_quantity(values["minimum_order_quantity"])
    await supplier.audit_as("Register the supplier for purchasing").save(context)


async def verify_failure(step, context, warehouse_id):
    try:
        await register_supplier(context, warehouse_id, step["input"])
    except CheckException as error:
        if len(error.violations) != 1:
            raise AssertionError(f"Expected one native checker result, received {error}") from error
        violation, = error.violations
        wire = violation.to_wire()
        key = {"required": "checker.required", "min": "checker.min"}[violation.rule_id.lower()]
        arguments = {"minimum": int(wire["systemValue"])} if key == "checker.min" else {}
        emit(step, context, "validation", case=step["case"], messageKey=key,
             nativeRule=violation.rule_id, location=violation.location.model_path,
             arguments=arguments, message=wire["message"],
             nativeArguments={name: wire[name] for name in ("inputValue", "systemValue") if name in wire})
    else:
        raise AssertionError(f"Invalid supplier registration was stored: {step['case']}")


async def main():
    plan = json.load(sys.stdin)
    client = SQLiteTeaQLClient(plan["database"])
    try:
        contexts = {name: create_context(client) for name in ("main", "independent")}
        await contexts["main"].ensure_schema()
        for step in plan["steps"]:
            context = contexts[step["context"]]
            operation = step["operation"]
            if operation == "select":
                try:
                    context.set_locale_code(step["locale"])
                except UnsupportedLocaleError as error:
                    emit(step, context, "locale", requestedLocale=error.locale_code,
                         accepted=False, nativeError=type(error).__name__)
                else:
                    emit(step, context, "locale", requestedLocale=step["locale"], accepted=True)
            elif operation == "validate":
                await verify_failure(step, context, plan["warehouse"]["id"])
            elif operation == "install-catalog":
                catalog = json.loads(Path(step["path"]).read_text(encoding="utf-8"))
                context.install_i18n_catalog(I18nCatalog.from_dict(catalog, I18nCatalog.builtin()))
                emit(step, context, "catalog-installed")
            elif operation == "verify-unchanged":
                rows = await (Q.suppliers_minimal().limit(1).comment("Check the rejected registrations")
                              .purpose("Verify no invalid supplier was stored").execute_for_list(context))
                emit(step, context, "storage", supplierCount=len(rows))
            else:
                raise ValueError(f"Unsupported example operation: {operation}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
