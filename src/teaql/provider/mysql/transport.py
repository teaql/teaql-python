import json
import aiomysql
from decimal import Decimal
from datetime import date, datetime
from typing import List, Dict, Any, Optional
from teaql.sql.executor import SqlTransport
from teaql.sql.types import CompiledQuery
from teaql.core.value import Value, DataType, Timestamp

class MysqlTransport(SqlTransport):
    def __init__(self, db_url: str):
        self.db_url = db_url

    def _parse_url(self):
        # basic simplistic parser for mysql://user:pass@host:port/db
        url = self.db_url.replace("mysql://", "")
        auth, host_path = url.split("@", 1)
        user, password = auth.split(":", 1)
        host_port, db = host_path.split("/", 1)
        if ":" in host_port:
            host, port = host_port.split(":", 1)
            port = int(port)
        else:
            host = host_port
            port = 3306
        return user, password, host, port, db

    def _bind_values(self, params: List[Value]) -> tuple:
        res = []
        for v in params:
            if v._data is None:
                res.append(None)
            elif getattr(v, '_type_hint', None) == DataType.Json or isinstance(v._data, (dict, list)):
                res.append(json.dumps(v._data))
            elif getattr(v, '_type_hint', None) == DataType.Timestamp or isinstance(v._data, Timestamp):
                if hasattr(v._data, "millis"):
                    res.append(datetime.fromtimestamp(v._data.millis / 1000.0))
                else:
                    res.append(v._data)
            else:
                res.append(v._data)
        return tuple(res)
        
    def _decode_value(self, val: Any) -> Any:
        if val is None:
            return None
        if isinstance(val, str) and val.startswith("{") and val.endswith("}"):
            try:
                return json.loads(val)
            except json.JSONDecodeError:
                pass
        if isinstance(val, datetime):
            return Timestamp(int(val.timestamp() * 1000))
        return val

    async def fetch_all_sql(self, query: CompiledQuery) -> List[Dict[str, Any]]:
        sql = query.sql_with_comment()
        params = self._bind_values(query.params)
        user, password, host, port, db = self._parse_url()
        
        conn = await aiomysql.connect(host=host, port=port, user=user, password=password, db=db, cursorclass=aiomysql.DictCursor)
        try:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)
                rows = await cur.fetchall()
                results = []
                for row in rows:
                    record = {}
                    for key, val in row.items():
                        record[key] = self._decode_value(val)
                    results.append(record)
                return results
        finally:
            conn.close()

    async def execute_sql(self, query: CompiledQuery) -> tuple[int, int]:
        sql = query.sql_with_comment()
        params = self._bind_values(query.params)
        user, password, host, port, db = self._parse_url()
        
        conn = await aiomysql.connect(host=host, port=port, user=user, password=password, db=db)
        try:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)
                await conn.commit()
                return cur.rowcount, cur.lastrowid
        finally:
            conn.close()
