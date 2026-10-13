from copy import deepcopy
from dataclasses import asdict, FrozenInstanceError
import gc
import weakref

import pytest

from teaql.core import QueryOperation, RequestIntentError, SelectQuery
from teaql.data_service import QueryRequest


def root(comment='load schools', purpose='render school list'):
    return QueryRequest(SelectQuery('School').comment(comment).purpose(purpose))


def details(request):
    return [node.comment for node in request.business_trace_chain]


def test_explicit_child_and_native_operation_have_distinct_parents():
    parent = root()
    child = parent.derive(SelectQuery('SchoolType').comment('load visible types'), 'school_type',
        QueryOperation('relation-select', 'select_school_type_with', relation='school_type'))
    assert child.root_request is parent
    assert child.parent_request.parent_request is parent
    assert child.local_comment == 'load visible types'
    assert details(child) == ['render school list', 'load schools', 'select_school_type_with(...)',
                             'load visible types']
    assert child._comment == parent._comment
    with pytest.raises(AttributeError):
        child.parent_request = child
    with pytest.raises(AttributeError):
        child.operation = QueryOperation('facet')  # read-only property, not a caller-owned field
    with pytest.raises(FrozenInstanceError):
        child.parent_request.operation.method = 'forged'


def test_missing_child_gets_local_default_but_missing_root_is_rejected():
    child = root().derive(SelectQuery('SchoolType'), 'school_type')
    assert child.local_comment == 'load SchoolType'
    with pytest.raises(RequestIntentError, match='REQUEST_COMMENT_REQUIRED'):
        QueryRequest(SelectQuery('School').purpose('render schools'))


@pytest.mark.parametrize('comment', ['', ' \n ', '\u0085'])
def test_explicit_blank_child_is_not_replaced_with_a_default(comment):
    with pytest.raises(RequestIntentError, match='REQUEST_COMMENT_REQUIRED'):
        root().derive(SelectQuery('SchoolType').comment(comment), 'school_type')


def test_clones_and_replacements_keep_private_ownership_and_the_physical_relation():
    parent = root()
    child = parent.derive(SelectQuery('SchoolType').comment('load labels'), 'school_type')
    updated = child.with_query(deepcopy(child.query).limit(3))
    captured = QueryRequest(deepcopy(updated.query))
    assert captured.root_request is parent
    assert captured.origin_entity == 'School'
    assert captured.local_comment == 'load labels'
    assert [(node.kind, node.name, node.comment) for node in captured.trace_chain] == [
        ('relation', 'school_type', 'School.school_type')]
    assert '_owner' not in asdict(captured.query)
    assert 'parent_request' not in asdict(captured.query)


def test_unrelated_invocation_cannot_replace_owned_query_even_with_identical_intent():
    first = QueryRequest(SelectQuery('School').comment('same comment').purpose('same purpose'))
    second = QueryRequest(SelectQuery('School').comment('same comment').purpose('same purpose'))
    with pytest.raises(ValueError, match='QUERY_SCOPE_OWNER_MISMATCH'):
        first.with_query(deepcopy(second.query))
    own_copy = first.with_query(deepcopy(first.query))
    own_copy.with_query(deepcopy(first.query))
    with pytest.raises(ValueError, match='QUERY_SCOPE_OWNER_MISMATCH'):
        own_copy.with_query(deepcopy(second.query))


def test_reusing_a_template_keeps_each_parent_and_does_not_mutate_the_template():
    template = SelectQuery('SchoolType').comment('load labels')
    first, second = root('first page'), root('second page')
    a, b = first.derive(template, 'school_type'), second.derive(template, 'school_type')
    assert a.root_request is first and b.root_request is second
    assert a.query is not b.query
    assert template.comment_text == 'load labels'
    assert not hasattr(template, 'purpose_text')
    assert 'second page' not in details(a)


def test_named_count_uses_centralized_native_escaping_and_no_physical_relation():
    parent = root()
    alias = "total'\\schools\n"
    operation = QueryOperation('named-count', 'count_as', alias)
    count = parent.for_count(alias, operation)
    assert count.local_comment == "count_as('total\\'\\\\schools\\n')"
    assert count.parent_request is parent
    assert count.query.aggregates[0].alias == alias
    assert count.trace_chain == []
    assert parent.query.aggregates == []


def test_facet_branches_share_one_operation_but_not_sibling_comments():
    parent = root()
    operation = parent.derive_operation(parent.query,
        QueryOperation('facet', 'facet_by_school_type_as', 'types', 'school_type'))
    aggregate = operation.derive_helper(SelectQuery('School'), 'aggregate school_type')
    values = operation.derive_child(SelectQuery('SchoolType').comment('load labels'), 'school_type')
    assert aggregate.parent_request is values.parent_request is operation
    assert details(aggregate)[-1] == 'aggregate school_type'
    assert details(values)[-1] == 'load labels'
    assert details(aggregate)[:3] == details(values)[:3]
    assert not aggregate.trace_chain


def test_prefixes_are_text_and_public_query_fields_cannot_forge_business_ancestry():
    query = SelectQuery('School').comment('what: load schools').purpose('why: render schools')
    query.parent_request = root('forged parent')
    query.business_trace_chain = ('forged chain',)
    captured = QueryRequest(query)
    assert details(captured) == ['why: render schools', 'what: load schools']
    assert captured.parent_request is None
    with pytest.raises(ValueError, match='QUERY_REQUEST_OWNERSHIP_INVALID'):
        QueryRequest(query, _binding=(object(), {}))


def test_identity_registry_does_not_keep_a_discarded_root_query_alive():
    request = root()
    reference = weakref.ref(request.query)
    del request
    gc.collect()
    assert reference() is None


def test_invalid_operations_and_alias_mismatch_use_value_free_diagnostics():
    with pytest.raises(ValueError, match='QUERY_OPERATION_INVALID') as error:
        QueryOperation('facet', "ILLEGAL-PRIVATE-CANARY\n")
    assert 'ILLEGAL-PRIVATE-CANARY' not in str(error.value)
    with pytest.raises(ValueError, match='QUERY_OPERATION_ALIAS_MISMATCH'):
        root().for_count('a', QueryOperation('named-count', 'count_as', 'b'))


def test_facet_reverse_aggregate_shares_operation_parent_and_keeps_physical_relations():
    parent = root()
    facet = parent.derive_operation(SelectQuery('School'),
        QueryOperation('facet', 'facet_by_school_type_as', 'types', 'school_type'))
    values = facet.derive_child(SelectQuery('SchoolType').comment('load visible types'), 'school_type')
    operation = QueryOperation('aggregate', 'sum_capacity_of_schools_as', 'capacity', 'school_list')
    aggregate = values.derive_aggregate(SelectQuery('School'), 'school_list', operation)
    assert aggregate.parent_request is facet
    assert aggregate.root_request is parent
    assert details(aggregate) == ['render school list', 'load schools', "facet_by_school_type_as('types')", 'aggregate school_type']
    assert [node.name for node in aggregate.trace_chain if node.kind == 'relation'] == ['school_type', 'school_list']
    explicit = values.derive_aggregate(SelectQuery('School').comment('sum visible capacity'), 'school_list', operation)
    assert details(explicit) == [*details(aggregate), 'sum visible capacity']
    with pytest.raises(RequestIntentError):
        values.derive_aggregate(SelectQuery('School').comment(' '), 'school_list', operation)
    assert values.local_comment == 'load visible types'


def test_relation_count_has_one_operation_request_without_inventing_a_value_load():
    parent = root()
    child = parent.derive_aggregate(SelectQuery('SchoolItem'), 'school_item_list',
        QueryOperation('relation-count', 'count_school_items_as', 'itemCount', 'school_item_list'))
    assert child.parent_request is parent
    assert details(child) == ['render school list', 'load schools', "count_school_items_as('itemCount')"]
