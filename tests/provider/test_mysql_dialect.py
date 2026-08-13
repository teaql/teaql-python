from teaql.core.expr import Expr
from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.query import SelectQuery
from teaql.core.value import DataType
from teaql.provider.mysql.dialect import MysqlDialect
from teaql.sql.types import DatabaseKind


class MockEntityDescriptor(EntityDescriptor):
    def __init__(self, name):
        super().__init__(name)
        self.properties = []


class MockPropertyDescriptor(PropertyDescriptor):
    def __init__(self, name, data_type, is_id=False):
        super().__init__(name, data_type)
        self.column_name = name
        self.property_type = data_type
        self.is_id_val = is_id

    def is_id(self):
        return self.is_id_val


def test_mysql_dialect_is_concrete_and_compiles_seek_query():
    entity = MockEntityDescriptor("Order")
    entity.table_name_val = "order"
    entity.properties = [MockPropertyDescriptor("id", DataType.I64, is_id=True)]
    query = SelectQuery("Order").order_desc("id").limit(10)
    query.and_filter(Expr.lt("id", 91))

    dialect = MysqlDialect()
    compiled = dialect.compile_select(entity, query)

    assert dialect.kind() == DatabaseKind.MySql
    assert "FROM `order`" in compiled.sql
    assert "id < %s" in compiled.sql
