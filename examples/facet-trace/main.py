import asyncio
import copy
import json
import os
from types import SimpleNamespace
from Q import Q
from E import E, TeaQLNotLoadedError
from models.school import School
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.core.list import SmartList
from teaql.provider.sqlite import create_sqlite_service
from teaql.runtime import UserContext

PRIVATE = 'FACET-PRIVATE-SCHOOL'
FUTURE = 'Campus Learning Platform'
PURPOSE = 'verify generated Facet ownership'

def school_facets(include_all, nested):
    types = Q.school_types().order_by_id_ascending().limit(10).count_as('school_count')
    if nested:
        types.facet_by_platform_as('platforms', Q.platforms().with_name_is(FUTURE)
            .order_by_id_ascending().limit(10).count_as('type_count'), include_all)
    return (Q.schools().with_name_in(PRIVATE, PRIVATE + '-B')
        .order_by_id_ascending().limit(1)
        .facet_by_school_type_as('types', types, include_all))

def assert_facets(rows, include_all, count, nested):
    assert isinstance(rows, SmartList), 'loaded relation must remain SmartList'
    types = rows.facet('types')
    assert isinstance(types, SmartList), 'requested empty Facet must remain present'
    pairs = [(row['id'], row['school_count']) for row in types]
    assert all(type(row['school_count']) is int for row in types), 'missing count is not zero'
    expected = [(1001, count), (1002, 0)] if include_all else ([(1001, count)] if count else [])
    assert pairs == expected, (pairs, expected)
    observation = {'types': pairs}
    if nested:
        platforms = types.facet('platforms')
        assert isinstance(platforms, SmartList), 'nested Facet was dropped'
        expected = [(1, 2)] if include_all else ([(1, 1)] if count else [])
        actual = [(row['id'], row['type_count']) for row in platforms]
        assert actual == expected, ('nested membership', actual, expected)
        observation['platforms'] = actual
    return observation

def log_row(entry):
    return {'comment': entry.comment, 'purpose': entry.purpose,
        'outcome': entry.execution_outcome, 'sql': entry.sql,
        'debug_sql': entry.debug_sql, 'params': [getattr(value, 'val', value) for value in entry.params],
        'path': [(n.kind, n.name, n.comment) for n in entry.trace_path]}

def assert_observed(context, diagnostics, reads, loaded, nested, logging):
    child = [('school_list', 'SchoolType.school_list')] if loaded else []
    first = child + [('school_type', 'School.school_type')]
    second = first + [('platform', 'SchoolType.platform')]
    branch = [child, first] + ([first, second] if nested else [])
    routes = [[], child, *branch, *branch] if loaded else [[], [], first] + ([first, second] if nested else [])
    assert len(reads) == len(routes), ('physical SQL count', len(reads), routes)
    assert sum('COUNT(' in sql.upper() for sql, _ in reads) == (4 if loaded else 2 if nested else 1)
    entries = context.sql_logs()
    assert len(entries) == len(diagnostics) == (len(reads) if logging else 0)
    if not logging:
        return
    root = 'SchoolType' if loaded else 'School'
    for entry, route in zip(entries, routes):
        assert entry.execution_outcome == 'success'
        assert entry.purpose == PURPOSE
        assert entry.comment.startswith('load ')
        assert [(n.kind, n.name, n.comment) for n in entry.trace_path] == [
            ('operation', root, 'query'), ('request', root, ''),
            *[('relation', name, detail) for name, detail in route],
            ('provider', 'sqlite', ''), ('sql', 'select', '')]
    safe = json.dumps([log_row(entry) for entry in entries + diagnostics])
    assert PRIVATE not in safe, 'private root binding leaked'
    if nested:
        assert FUTURE not in safe, 'future-only Facet binding leaked before first root SQL'

async def main():
    service = create_sqlite_service(os.environ['TEAQL_FACET_TRACE_DB'])
    context = UserContext.new().install(GENERATED_RUNTIME_MODULE).insert_resource('dataService', service)
    diagnostics, reads, policies = [], [], []
    context.set_diagnostic_sql_log_sink(SimpleNamespace(write=diagnostics.append))
    await context.ensure_schema()
    for suffix in ('', '-B'):
        name = PRIVATE + suffix
        existing = await (Q.schools().with_name_is(name).limit(1).comment('find retained fixture')
            .purpose('idempotent seed').execute_for_list(context))
        if not existing:
            school = Q.schools().comment('initialize fixture').purpose('idempotent seed').new_entity(context)
            (school.update_platform(1).update_school_type(1001).update_name(name)
                .update_address('12 River Road').update_established_date('1995-09-01')
                .update_student_capacity(800).update_active(True))
            await school.audit_as('seed generated Facet acceptance').save(context)
    original_fetch = service.transport.fetch_all_sql
    async def capture(compiled):
        reads.append((compiled.sql, [value.val for value in compiled.params]))
        return await original_fetch(compiled)
    service.transport.fetch_all_sql = capture
    def policy(query):
        policies.append(query.comment_text)
        return query
    context.with_request_policy(policy)
    failures, cases = [], 0
    for mode in ('root', 'nested', 'loaded'):
        for include_all in (True, False):
            for logging in (True, False):
                for empty in ((False,) if mode == 'loaded' else (False, True)):
                    label = (mode, include_all, logging, empty)
                    context.enable_all_sql_log() if logging else context.disable_sql_log()
                    context.clear_sql_logs(); diagnostics.clear(); reads.clear(); policies.clear()
                    nested = mode != 'root'
                    request = school_facets(include_all, nested)
                    if empty: request.with_name_is('absent')
                    if mode == 'loaded':
                        request.top_n_probe_parent_threshold(0)
                        request = (Q.school_types().order_by_id_ascending().limit(10)
                            .select_school_list_with(request))
                    comment = 'load ' + PRIVATE + (' via ' + FUTURE if nested else '')
                    executable = request.comment(comment).purpose(PURPOSE)
                    before = copy.deepcopy(request.query)
                    try:
                        rows = await executable.execute_for_list(context)
                        assert request.query == before, 'execution mutated caller query'
                        assert policies[0] == comment, 'safe projection changed policy intent'
                        assert_observed(context, diagnostics, reads, mode == 'loaded', nested, logging)
                        if mode == 'loaded':
                            assert [E.school_type(parent).id().eval() for parent in rows] == [1001, 1002]
                            results = []
                            for parent in rows:
                                own_count = 2 if E.school_type(parent).id().eval() == 1001 else 0
                                assert E.school_type(parent).school_list().size().eval() == int(bool(own_count))
                                children = parent.school_list()
                                if children:
                                    assert isinstance(children[0], School)
                                    assert E.school(children[0]).name().eval() == PRIVATE
                                results.append({'parent_id': E.school_type(parent).id().eval(),
                                    'visible_rows': len(children),
                                    'facets': assert_facets(children, include_all, own_count, True)})
                        else:
                            assert len(rows) == (0 if empty else 1)
                            if rows:
                                assert isinstance(rows[0], School)
                                assert E.school(rows[0]).name().eval() == PRIVATE
                            results = [{'visible_rows': len(rows),
                                'facets': assert_facets(rows, include_all, 0 if empty else 2, nested)}]
                        assert any(PRIVATE in params for _, params in reads), 'real root bind was changed'
                        if nested:
                            assert any(FUTURE in params for _, params in reads), 'real future bind was changed'
                        print('FACET_OBSERVED ' + json.dumps({'case': label, 'calls': len(reads),
                            'counts': sum('COUNT(' in sql.upper() for sql, _ in reads),
                            'results': results,
                            'sql': [log_row(entry) for entry in context.sql_logs()]}))
                        cases += 1
                    except Exception as error:
                        failures.append((label, type(error).__name__, str(error)))
                        print('FACET_FAILURE', failures[-1])
    context.enable_all_sql_log(); context.clear_sql_logs(); diagnostics.clear(); reads.clear()
    independent = await (Q.school_types().with_id_is(1001).limit(1)
        .comment('independent ' + PRIVATE).purpose('no inherited Facet redaction').execute_for_list(context))
    assert context.sql_logs()[0].comment == 'independent ' + PRIVATE
    try: E.school_type(independent[0]).school_list().size().eval()
    except TeaQLNotLoadedError: pass
    else: raise AssertionError('unselected relation stopped being NotLoaded')
    await service.close()
    assert not failures, failures
    assert cases == 20, cases
    print('PASS: Python generated Facets; 20 root/nested/loaded/empty/includeAll/logging scenarios; Q/E/save; retained SQLite')

asyncio.run(main())
