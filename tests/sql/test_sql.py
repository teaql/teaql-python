import pytest
from teaql.core.query import SelectQuery, OrderBy, SortDirection, Slice
from teaql.core.mutation import InsertMutation, UpdateMutation, DeleteMutation, RecoverMutation
from teaql.core.expr import Expr, ExprBuilder
from teaql.core.value import Value, DataType
from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.sql.dialect import SqlDialect, quote_identifier_if_needed
from teaql.sql.types import DatabaseKind, CompiledQuery, SqlCompileError, EmptyInListError, MissingIdPropertyError

class TestDialect(SqlDialect):
    def kind(self) -> DatabaseKind:
        return DatabaseKind.PostgreSql
    
    def quote_ident(self, ident: str) -> str:
        return f'"{ident}"'
        
    def placeholder(self, index: int) -> str:
        return f"${index}"

ORDER_DEFAULT_PROJECTION = '"id", "version", "name"'

class MyEntityDescriptor(EntityDescriptor):
    def __init__(self, name, table_name, properties):
        super().__init__(name)
        self.table_name_val = table_name
        self.properties = properties
        
    def id_property(self):
        return next((p for p in self.properties if getattr(p, 'is_id_val', False)), None)
        
    def version_property(self):
        return next((p for p in self.properties if getattr(p, 'is_version_val', False)), None)

class MyPropertyDescriptor(PropertyDescriptor):
    def __init__(self, name, column_name, data_type, is_id_val=False, is_version_val=False, nullable=True):
        super().__init__(name, data_type)
        self.column_name = column_name
        self.is_id_val = is_id_val
        self.is_version_val = is_version_val
        self.nullable = nullable
        
    def is_id(self): return self.is_id_val
    def is_version(self): return self.is_version_val

def entity() -> EntityDescriptor:
    return MyEntityDescriptor("Order", "orders", [
        MyPropertyDescriptor("id", "id", DataType.U64, is_id_val=True, nullable=False),
        MyPropertyDescriptor("version", "version", DataType.I64, is_version_val=True, nullable=False),
        MyPropertyDescriptor("name", "name", DataType.Text)
    ])

def test_quotes_identifiers_only_when_needed():
    assert quote_identifier_if_needed("stock_item_data", '"') == "stock_item_data"
    assert quote_identifier_if_needed("select", '"') == '"select"'
    assert quote_identifier_if_needed("order", '`') == '`order`'
    assert quote_identifier_if_needed("has space", '"') == '"has space"'
    assert quote_identifier_if_needed('"already_wrapped"', '"') == '"already_wrapped"'

def test_compiles_select_with_filters_order_and_limit():
    q = SelectQuery.new("Order")
    q.projection = ["id", "name"]
    q.filter = ExprBuilder.column("name") # Will be replaced below
    
    from teaql.core.expr import BinaryExpr, BinaryOp, ColumnExpr, ValueExpr
    q.filter = BinaryExpr(ColumnExpr("name"), BinaryOp.Eq, ValueExpr(Value.from_any("A")))
    q.order_desc("id")
    q.slice = Slice(limit=10, offset=5)
    
    dialect = TestDialect()
    compiled = dialect.compile_select(entity(), q)
    
    assert compiled.sql == 'SELECT "id", "name" FROM "orders" WHERE ("name" = $1) ORDER BY "id" DESC LIMIT 10 OFFSET 5'
    assert compiled.params == [Value.from_any("A")]

def test_compiles_aggregate_projection():
    q = SelectQuery.new("Order").count("count")
    dialect = TestDialect()
    compiled = dialect.compile_select(entity(), q)
    assert compiled.sql == 'SELECT COUNT("id") AS "count" FROM "orders"'

def test_compiles_insert_update_delete_and_recover():
    dialect = TestDialect()
    
    insert = InsertMutation.new("Order").value("id", 1).value("name", "A")
    compiled_insert = dialect.compile_insert(entity(), insert)
    # The order of values might depend on dictionary iteration, but let's assume id then name
    assert compiled_insert.sql == 'INSERT INTO "orders" ("id", "name") VALUES ($1, $2)'
    
    update = UpdateMutation.new("Order", 1).with_expected_version(3).value("name", "B")
    compiled_update = dialect.compile_update(entity(), update)
    assert compiled_update.sql == 'UPDATE "orders" SET "name" = $1, "version" = $2 WHERE "id" = $3 AND "version" = $4'
    
    delete = DeleteMutation.new("Order", 1).with_expected_version(3)
    compiled_delete = dialect.compile_delete(entity(), delete)
    assert compiled_delete.sql == 'UPDATE "orders" SET "version" = $1 WHERE "id" = $2 AND "version" = $3'
    
    recover = RecoverMutation.new("Order", 1, -4)
    compiled_recover = dialect.compile_recover(entity(), recover)
    assert compiled_recover.sql == 'UPDATE "orders" SET "version" = $1 WHERE "id" = $2 AND "version" = $3'

def test_compiles_in_expression_and_validates_empty_list():
    dialect = TestDialect()
    from teaql.core.expr import BinaryExpr, BinaryOp, ColumnExpr, ValueExpr
    
    q = SelectQuery.new("Order")
    q.filter = BinaryExpr(ColumnExpr("id"), BinaryOp.In, ValueExpr(Value.List([Value.from_any(1), Value.from_any(2)])))
    compiled = dialect.compile_select(entity(), q)
    assert compiled.sql == f'SELECT {ORDER_DEFAULT_PROJECTION} FROM "orders" WHERE ("id" IN ($1, $2))'
    
    q2 = SelectQuery.new("Order")
    q2.filter = BinaryExpr(ColumnExpr("id"), BinaryOp.In, ValueExpr(Value.List([])))
    with pytest.raises(EmptyInListError):
        dialect.compile_select(entity(), q2)
