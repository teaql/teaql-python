from teaql.core.query import FacetRequest, RelationLoad, SelectQuery
from teaql.runtime.context import UserContext


def test_prepare_query_clones_and_governs_every_query_node_once():
    shared = SelectQuery("SchoolType").project("id")
    root = SelectQuery("School").project("id")
    root.relations.append(RelationLoad("schoolType", shared))
    root.facets.append(FacetRequest("types", "schoolType", shared))
    calls = []

    def policy(query):
        calls.append(query.entity)
        query.project("policy_marker")

    context = UserContext().with_request_policy(policy)
    prepared = context.prepare_query(root)

    assert prepared is not root
    assert prepared.relations[0].query is prepared.facets[0].query
    assert calls == ["School", "SchoolType"]
    assert "policy_marker" in prepared.projection
    assert "policy_marker" in prepared.relations[0].query.projection
    assert "policy_marker" not in root.projection
    assert "policy_marker" not in shared.projection


def test_prepare_query_without_policy_still_returns_independent_graph():
    child = SelectQuery("SchoolType").project("id")
    root = SelectQuery("School")
    root.relations.append(RelationLoad("schoolType", child))

    prepared = UserContext().prepare_query(root)
    prepared.relations[0].query.project("code")

    assert prepared is not root
    assert prepared.relations[0].query is not child
    assert child.projection == ["id"]


def test_prepare_query_propagates_policy_denial():
    def deny(query):
        if query.entity == "SchoolType":
            raise PermissionError("query policy denied SchoolType")

    root = SelectQuery("School")
    root.relations.append(RelationLoad("schoolType", SelectQuery("SchoolType")))

    context = UserContext().with_request_policy(deny)
    try:
        context.prepare_query(root)
    except PermissionError as error:
        assert str(error) == "query policy denied SchoolType"
    else:
        raise AssertionError("nested policy denial must fail closed")


def test_prepare_query_preserves_shared_nodes_when_policy_returns_replacement():
    shared = SelectQuery("SchoolType")
    root = SelectQuery("School")
    root.relations.append(RelationLoad("schoolType", shared))
    root.facets.append(FacetRequest("types", "schoolType", shared))

    def replace(query):
        replacement = SelectQuery(query.entity)
        replacement.relations = query.relations
        replacement.facets = query.facets
        replacement.project("authorized")
        return replacement

    prepared = UserContext().with_request_policy(replace).prepare_query(root)

    assert prepared.relations[0].query is prepared.facets[0].query
    assert prepared.relations[0].query.projection == ["authorized"]
