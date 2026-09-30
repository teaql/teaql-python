from teaql.core.query import FacetRequest, RelationLoad, SelectQuery
from teaql.runtime import UserContext


shared = SelectQuery("SchoolType").project("id")
original = SelectQuery("School").project("id")
original.relations.append(RelationLoad("schoolType", shared))
original.facets.append(FacetRequest("types", "schoolType", shared))
calls = []


def tenant_policy(query):
    calls.append(query.entity)
    if query.entity == "ForbiddenReport":
        raise PermissionError("query policy denied ForbiddenReport")
    query.project("tenant_id")


context = UserContext.new().with_request_policy(tenant_policy)
authorized = context.prepare_query(original)

assert authorized is not original
assert authorized.relations[0].query is authorized.facets[0].query
assert calls == ["School", "SchoolType"]
assert "tenant_id" in authorized.projection
assert "tenant_id" not in original.projection
assert "tenant_id" not in shared.projection

try:
    context.prepare_query(SelectQuery("ForbiddenReport"))
except PermissionError as error:
    assert str(error) == "query policy denied ForbiddenReport"
else:
    raise AssertionError("query policy denial must fail closed")

print("PASS Python Query Policy example")
