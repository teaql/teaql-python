"""Repository-local generated seed/Q/E example; no SDK setup or manual spans."""
import asyncio
import os
import sys
import tempfile
from pathlib import Path
from Q import Q
from E import E
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.runtime import UserContext
from teaql.provider.sqlite import create_sqlite_service


class AuditSink:
    def __init__(self):
        self.count = 0

    async def on_safe_event(self, context, event):
        self.count += 1


async def main():
    directory = Path(tempfile.mkdtemp(prefix='teaql-python-standard-'))
    database = directory / 'example.sqlite'
    context = UserContext.new().install(GENERATED_RUNTIME_MODULE)
    service = create_sqlite_service(str(database))
    audit = AuditSink()
    context.insert_resource('dataService', service).with_app_audit_event_sink(audit)
    context.disable_sql_log()
    try:
        await context.ensure_schema()
        first = audit.count
        await context.ensure_schema()
        assert first == audit.count == 1, 'one committed seed; no repeated seed write'
        for _ in range(2):
            rows = await Q.platforms().with_id_is(1).limit(1).comment('load seeded platform').purpose(
                'verify standard telemetry through generated Q and E').execute_for_list(context)
            assert len(rows) == 1 and E.platform(rows[0]).id().eval() == 1 and E.platform(rows[0]).name().eval()
        assert not context.sql_logs(), 'ordinary SQL logging stays off'
        if os.environ.get('TEAQL_TELEMETRY_ENABLED', '').lower() != 'true':
            assert not any(name.startswith('opentelemetry') for name in sys.modules), 'disabled SDK import'
        await asyncio.to_thread(context.runtime_telemetry().flush)
        print(f'PYTHON_STANDARD_TELEMETRY_EXAMPLE PASSED first_seed_audits=1 repeat_seed_audits=0 queries=2 ordinary_sql_logs=0 database={database}')
    finally:
        await service.close()
        await asyncio.to_thread(context.runtime_telemetry().shutdown)


if __name__ == '__main__':
    asyncio.run(main())
