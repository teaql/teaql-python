"""Generated Order Q/E and audited seed replay; no application SDK setup."""
import asyncio
from datetime import date
from decimal import Decimal
import os
from pathlib import Path
import sys
import tempfile
from uuid import uuid4

from Q import Q
from E import E
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.data_service import SQLiteTeaQLClient
from teaql.runtime import UserContext


class Audits:
    def __init__(self):
        self.count = 0

    async def on_safe_event(self, context, event):
        self.count += 1


async def main():
    database = os.environ.get('TEAQL_STANDARD_ORDER_DB')
    if not database:
        database = str(Path(tempfile.mkdtemp(prefix='teaql-python-order-')) / 'orders.sqlite')
    service = SQLiteTeaQLClient(database)
    context = UserContext.new().install(GENERATED_RUNTIME_MODULE).insert_resource('dataService', service)
    assert context.entity('CustomerOrder') is not None, 'standard Order metadata missing'
    context.configure_audit_policy('CustomerOrder', ['order_number'])
    audit = Audits()
    context.with_app_audit_event_sink(audit).disable_sql_log()
    try:
        await context.ensure_schema()
        first = audit.count
        assert first in (0, 4), 'generated platform and three constants'
        await context.ensure_schema()
        assert audit.count == first, 'repeated schema must not write more seeds'
        platforms = await (Q.platforms().with_id_is(1).limit(1).comment('load seeded platform')
                           .purpose('prepare standard Order graph').execute_for_list(context))
        assert len(platforms) == 1 and E.platform(platforms[0]).id().eval() == 1
        secret = 'ORDER-PRIVATE-' + uuid4().hex
        customer = Q.customers().comment('create standard customer').purpose('prepare Order graph').new_entity(context)
        customer.update_name('North Star Retail').update_platform(platforms[0])
        await customer.audit_as('seed standard customer').save(context)
        for index in range(1, 5):
            order = Q.customer_orders().comment('create standard order').purpose('prepare Order graph').new_entity(context)
            order.update_customer(customer).update_order_number(f'{secret}-{index:03}' if index < 4 else 'OTHER-004')
            order.update_order_date(date(2026, 10, index)).update_total_amount(Decimal(index * 100 if index < 4 else 900))
            if index == 1:
                order.update_status_to_new()
            else:
                order.update_status_to_paid()
            await order.audit_as('seed standard order').save(context)
            for item in range(1, 6):
                line = Q.order_items().comment('create standard item').purpose('prepare bounded previews').new_entity(context)
                line.update_customer_order(order).update_product_name(f'Box {item}').update_quantity(item)
                line.update_unit_price(Decimal(20))
                await line.audit_as('seed standard item').save(context)
        for repetition in range(4):
            counted = repetition < 2
            request = (Q.customer_orders_minimal().with_order_number_containing(secret)
                .facet_by_status_as('statusCounts', Q.order_statuses_minimal()
                    .select_name().select_color().count_as('orderCount')
                    .sum_total_amount_of_customer_orders_as('orderTotalAmount', Q.customer_orders_minimal())
                    .order_by_display_order_ascending().comment('load status facets'))
                .select_order_number().select_order_date()
                .select_status_with(Q.order_statuses_minimal().select_name().select_color().comment('load status'))
                .select_order_item_list_with(Q.order_items_minimal().select_product_name().select_quantity()
                    .order_by_id_ascending().limit(3).comment('load item previews'))
                .count_order_items_as('itemCount').order_by_order_date_descending().order_by_id_descending()
                .offset(1).limit(1).comment('load order list'))
            if counted:
                request.count_as('totalOrders')
            rows = await request.purpose('render order list page').execute_for_list(context)
            assert len(rows) == 1
            if counted:
                assert rows.total_count == rows.aggregations['totalOrders'] == 3
            else:
                assert rows.aggregations == {}, 'ordinary list does not request an exact total'
            row = rows[0]
            assert E.customer_order(row).order_number().eval() == secret + '-002'
            assert E.customer_order(row).order_date().eval() == date(2026, 10, 2)
            assert E.customer_order(row).status().name().eval() == 'Paid'
            assert E.customer_order(row).order_item_list().size().eval() == 3
            assert E.customer_order(row).order_item_list().first().product_name().eval() == 'Box 1'
            assert row.get_dynamic_property('itemCount') == 5
            facets = rows.facets['statusCounts']
            assert [(f['id'], f['orderCount'], f['orderTotalAmount']) for f in facets] == [
                (1001, 1, Decimal(100)), (1002, 2, Decimal(500)), (1003, 0, None)]
        assert audit.count == first + 25 and not context.sql_logs()
        if os.environ.get('TEAQL_TELEMETRY_ENABLED', '').lower() != 'true':
            assert not any(name.startswith('opentelemetry') for name in sys.modules)
        await asyncio.to_thread(context.runtime_telemetry().flush)
        print(f'PYTHON_STANDARD_ORDER PASSED queries=4 counted=2 uncounted=2 total=3 preview=3 itemCount=5 facets=3 '
              f'first_seed_audits={first} repeat_seed_audits=0 audits={audit.count} ordinary_sql_logs=0 database={database}')
    finally:
        await service.close()
        await asyncio.to_thread(context.runtime_telemetry().shutdown)


if __name__ == '__main__':
    asyncio.run(main())
