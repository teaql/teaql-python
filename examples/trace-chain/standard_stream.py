"""Generated Q/E scalar streams; no application SDK setup or manual spans."""
import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
from uuid import uuid4

from Q import Q
from E import E
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.provider.sqlite import create_sqlite_service
from teaql.runtime import UserContext


class Audits:
    count = 0
    async def on_safe_event(self, context, event):
        self.count += 1


async def main():
    database = os.environ.get('TEAQL_STANDARD_STREAM_DB') or str(
        Path(tempfile.mkdtemp(prefix='teaql-python-stream-')) / 'streams.sqlite')
    context = UserContext.new().install(GENERATED_RUNTIME_MODULE)
    service = create_sqlite_service(database)
    audits = Audits()
    context.insert_resource('dataService', service).with_app_audit_event_sink(audits).disable_sql_log()
    nonce = uuid4().hex.translate(str.maketrans('0123456789', 'klmnopqrst'))
    try:
        await context.ensure_schema()
        first = audits.count
        await context.ensure_schema()
        assert audits.count == first and first in (0, 1)
        platform = await (Q.platforms().with_id_is(1).limit(1).comment('load stream platform')
            .purpose('prepare standard scalar streams').execute_for_one(context))
        ids = []
        for index in range(3):
            row = Q.customer_orders().comment('create scalar stream row').purpose('prepare bounded stream input').new_entity(context)
            row.update_platform(platform).update_order_number('STREAM-' + nonce + str(index)).update_description('Scalar stream row')
            await row.audit_as('seed scalar stream row').save(context)
            ids.append(E.customer_order(row).id().eval())

        builder = Q.customer_orders().with_id_in(*ids).order_by_id_ascending().limit(3)
        first_stream = builder.comment('complete standard stream').purpose('verify actual scalar stream diagnostics').execute_for_stream(context, chunk_size=2)
        second_stream = (Q.customer_orders().with_id_in(*ids).order_by_id_ascending().limit(3)
            .comment('close standard stream early').purpose('verify actual scalar stream diagnostics').execute_for_stream(context, chunk_size=2))
        untouched = (Q.customer_orders().with_id_in(*ids).limit(3).comment('unpolled standard stream')
            .purpose('verify actual scalar stream diagnostics').execute_for_stream(context, chunk_size=2))
        await untouched.aclose()
        builder.with_id_is(9223372036854775807).comment('LATE-STREAM-COMMENT').purpose('LATE-STREAM-PURPOSE')
        first_row, second_row = await anext(first_stream), await anext(second_stream)
        assert E.customer_order(first_row).id().eval() == E.customer_order(second_row).id().eval() == ids[0]
        independent = await (Q.customer_orders().with_id_is(ids[0]).limit(1).comment('independent between standard streams')
            .purpose('verify idle stream isolation').execute_for_list(context))
        assert len(independent) == 1
        await second_stream.aclose()
        remaining = [row async for row in first_stream]
        await first_stream.aclose()
        rows = [first_row, *remaining]
        assert [E.customer_order(row).id().eval() for row in rows] == ids
        assert len({id(row._entity_root) for row in rows}) == 3
        assert audits.count == first + 3 and not context.sql_logs()
        if os.environ.get('TEAQL_TELEMETRY_ENABLED', '').lower() != 'true':
            assert not any(name.startswith('opentelemetry') for name in sys.modules)
        await asyncio.to_thread(context.runtime_telemetry().flush)
        print('PYTHON_STANDARD_STREAM_FACTS ' + json.dumps({'first_seed_audits': first, 'repeat_seed_audits': 0,
            'complete': 3, 'early_close': 1, 'independent': 1, 'unpolled': 0, 'chunk_size': 2}, sort_keys=True))
        print('PYTHON_STANDARD_STREAM PASSED complete=3 early_close=1 independent=1 ordinary_sql_logs=0')
    finally:
        await service.close()
        await asyncio.to_thread(context.runtime_telemetry().shutdown)


if __name__ == '__main__':
    asyncio.run(main())
