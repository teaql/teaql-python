import json
import aiosqlite
from decimal import Decimal
from datetime import date
from typing import List, Dict, Any, Optional
from teaql.sql.executor import SqlTransport
from teaql.sql.types import CompiledQuery
from teaql.core.value import Value, DataType, Timestamp

class SqliteTransport(SqlTransport):
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _bind_values(self, params: List[Value]) -> tuple:
        res = []
        for v in params:
            if v._data is None:
                res.append(None)
            elif isinstance(v._data, bool):
                res.append(1 if v._data else 0)
            elif isinstance(v._data, Decimal):
                res.append(f"__teaql_decimal__:{v._data}")
            elif getattr(v, '_type_hint', None) == DataType.Json or isinstance(v._data, (dict, list)):
                res.append(json.dumps(v._data))
            elif getattr(v, '_type_hint', None) == DataType.Date or isinstance(v._data, date):
                if hasattr(v._data, "strftime"):
                    res.append(v._data.strftime("%Y-%m-%d"))
                else:
                    res.append(str(v._data))
            elif getattr(v, '_type_hint', None) == DataType.Timestamp or isinstance(v._data, Timestamp):
                if hasattr(v._data, "millis"):
                    res.append(str(v._data.millis))
                else:
                    res.append(str(v._data))
            else:
                res.append(v._data)
        return tuple(res)
        
    def _decode_value(self, val: Any) -> Any:
        if val is None:
            return None
        if isinstance(val, str):
            if val.startswith("__teaql_decimal__:"):
                return Decimal(val.split(":", 1)[1])
        return val

    async def fetch_all_sql(self, query: CompiledQuery) -> List[Dict[str, Any]]:
        sql = query.sql_with_comment()
        params = self._bind_values(query.params)
        
        is_uri = self.db_path.startswith("file:")
        async with aiosqlite.connect(self.db_path, uri=is_uri) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
                if not rows:
                    return []
                
                columns = [col[0] for col in cursor.description]
                results = []
                for row in rows:
                    record = {}
                    for idx, col_name in enumerate(columns):
                        val = row[idx]
                        record[col_name] = self._decode_value(val)
                    results.append(record)
                return results

    async def execute_sql(self, query: CompiledQuery) -> int:
        sql = query.sql_with_comment()
        params = self._bind_values(query.params)
        
        is_uri = self.db_path.startswith("file:")
        async with aiosqlite.connect(self.db_path, uri=is_uri) as db:
            async with db.execute(sql, params) as cursor:
                await db.commit()
                return cursor.rowcount
