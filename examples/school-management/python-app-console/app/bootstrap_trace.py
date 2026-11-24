"""Generated bootstrap acceptance; observe outputs, never inject trace frames."""
import asyncio
import os
from pathlib import Path
import sqlite3

from Q import Q
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.data_service import SQLiteTeaQLClient
from teaql.runtime import UserContext
from teaql.runtime.context import SqlLogOptions


def identity(node):
    return node.name or node.entity_type, node.entity_id


class Evidence:
    def __init__(self, database):
        self.database, self.events, self.sql = database, [], []
        self.versions = {('Platform', 1): 1, ('SchoolType', 1001): 1, ('SchoolType', 1002): 1}

    def write(self, entry):
        self.sql.append(entry)

    def on_safe_event(self, context, event):
        key = event.entity, getattr(event.entity_id, 'val', event.entity_id)
        table = {'Platform': 'platform_data', 'SchoolType': 'school_type_data'}[event.entity]
        # Read-only, independent connection: audit must follow durable commit.
        with sqlite3.connect(self.database.as_uri() + '?mode=ro', uri=True, timeout=1) as connection:
            row = connection.execute(f'SELECT version FROM {table} WHERE id = ?', (key[1],)).fetchone()
        assert row == (self.versions[key],), (key, row, self.versions[key])
        self.events.append(event)

    def clear(self, context):
        self.sql.clear()
        self.events.clear()
        context.clear_sql_logs()

    def verify(self, writes, reads, logging):
        assert len(self.events) == writes, self.events
        audits = {}
        for event in self.events:
            assert event.actor == 'teaql-generated-bootstrap', event.actor
            assert event.category == 'runtime-bootstrap', event.category
            assert len(event.trace_chain) == 1, event.trace_chain
            node = event.trace_chain[0]
            assert node.kind == 'auditReason' and node.comment.strip(), node
            key = event.entity, getattr(event.entity_id, 'val', event.entity_id)
            assert identity(node) == key, (node, key)
            audits[key] = node
        if not logging:
            assert self.sql == [], self.sql
            return
        mutations = [entry for entry in self.sql if entry.operation.name.lower() != 'select']
        assert len(mutations) == writes, mutations
        assert len(self.sql) - writes == reads, len(self.sql)
        for entry in self.sql:
            select = entry.operation.name.lower() == 'select'
            assert [node.kind for node in entry.trace_path] == [
                'operation', 'request' if select else 'entity', 'provider', 'sql'], entry.trace_path
            if select:
                assert entry.comment and entry.purpose, entry
            else:
                assert len(entry.mutation_lineage) == 1, entry
                node = entry.mutation_lineage[0]
                assert node == audits[identity(node)], (node, audits)
                assert entry.audit_reason == node.comment, (entry.audit_reason, node)


async def main():
    database = Path(os.environ['TEAQL_SCHOOL_BOOTSTRAP_DB']).resolve()
    logging = os.environ['TEAQL_SCHOOL_BOOTSTRAP_LOGGING'] == 'on'
    evidence = Evidence(database)
    client = SQLiteTeaQLClient(str(database))
    context = (UserContext.new().install(GENERATED_RUNTIME_MODULE)
        .insert_resource('dataService', client).with_user_identifier('school-example-user')
        .with_app_audit_event_sink(evidence))
    context.set_diagnostic_sql_log_sink(evidence)
    context.with_sql_log_options(SqlLogOptions.all() if logging else SqlLogOptions.disabled())
    await context.ensure_schema()
    fresh = len(evidence.events) == 3
    evidence.verify(3 if fresh else 0, 6 if fresh else 3, logging)
    assert context.user_identifier() == 'school-example-user'
    evidence.clear(context)
    await context.ensure_schema()
    evidence.verify(0, 3, logging)
    primary = await (Q.school_types().with_id_is(1001).limit(1)
        .comment('load Primary for audited drift').purpose('verify bootstrap reconciliation')
        .execute_for_one(context))
    original_version = primary.version
    evidence.versions[('SchoolType', 1001)] = original_version + 1
    primary.update_name('Drifted Primary')
    await primary.audit_as('simulate constant drift').save(context)
    assert len(evidence.events) == 1
    assert evidence.events[0].actor == 'school-example-user'
    assert evidence.events[0].category != 'runtime-bootstrap'
    evidence.clear(context)
    evidence.versions[('SchoolType', 1001)] = original_version + 2
    await context.ensure_schema()
    evidence.verify(1, 4, logging)
    restored = await (Q.school_types().with_id_is(1001).limit(1)
        .comment('verify corrected constant').purpose('verify audited bootstrap persistence')
        .execute_for_one(context))
    assert restored.name == 'Primary' and restored.version == original_version + 2
    evidence.clear(context)
    await context.ensure_schema()
    evidence.verify(0, 3, logging)
    assert context.user_identifier() == 'school-example-user'
    print(f'PASS Python generated bootstrap trace logging={logging} fresh={fresh} originalVersion={original_version}')


if __name__ == '__main__':
    asyncio.run(main())
