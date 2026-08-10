from teaql.core.query import SelectQuery
q = SelectQuery("User")
print("group_by type:", type(q.group_by))
