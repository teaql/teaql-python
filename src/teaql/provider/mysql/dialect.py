from teaql.sql.dialect import SqlDialect
from teaql.core.meta import EntityDescriptor

class MysqlDialect(SqlDialect):
    def quote_identifier(self, identifier: str) -> str:
        return f"`{identifier}`"
        
    def placeholder(self, index: int) -> str:
        return "%s"
        
    def compile_create_table(self, entity: EntityDescriptor) -> str:
        lines = []
        lines.append(f"CREATE TABLE IF NOT EXISTS {self.quote_identifier(entity.table_name)} (")
        cols = []
        for prop in entity.properties:
            col_type = "TEXT"
            if prop.type == "U64" or prop.type == "I64":
                col_type = "BIGINT"
            elif prop.type == "Timestamp":
                col_type = "BIGINT"
            elif prop.type == "Bool":
                col_type = "TINYINT(1)"
            
            if prop.name == "id":
                cols.append(f"  {self.quote_identifier(prop.column_name)} {col_type} PRIMARY KEY")
            else:
                cols.append(f"  {self.quote_identifier(prop.column_name)} {col_type}")
        
        lines.append(",\n".join(cols))
        lines.append(")")
        return "\n".join(lines)
