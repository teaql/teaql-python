import json
import aiosqlite
from decimal import Decimal
from datetime import date
from typing import List, Dict, Any, Optional, AsyncIterator
from teaql.sql.executor import SqlTransactionTransport, SqlTransactionTransportTx
from teaql.sql.types import CompiledQuery
from teaql.core.value import Value, DataType, Timestamp

def _soundex(value: Optional[str]) -> str:
    if value is None:
        return "?000"
    letters = [char.upper() for char in str(value) if char.isascii() and char.isalpha()]
    if not letters:
        return "?000"
    groups = {
        **dict.fromkeys("BFPV", "1"), **dict.fromkeys("CGJKQSXZ", "2"),
        **dict.fromkeys("DT", "3"), "L": "4", **dict.fromkeys("MN", "5"), "R": "6",
    }
    result = letters[0]
    previous = groups.get(letters[0], "0")
    for letter in letters[1:]:
        current = groups.get(letter, "0")
        if current != "0" and current != previous:
            result += current
            if len(result) == 4:
                break
        previous = current
    return result.ljust(4, "0")

class SqliteTransport(SqlTransactionTransport):
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._soundex_enabled = False

    async def enable_soundex(self) -> None:
        self._soundex_enabled = True

    async def _prepare(self, db: aiosqlite.Connection) -> None:
        if self._soundex_enabled:
            await db.create_function("soundex", 1, _soundex, deterministic=True)

    def _bind_values(self, params: List[Value]) -> tuple:
        res = []
        for v in params:
            if v._data is None:
                res.append(None)
            elif isinstance(v._data, bool):
                res.append(1 if v._data else 0)
            elif isinstance(v._data, Decimal):
                # SQLite applies NUMERIC affinity to an ordinary decimal string.
                # A tagged transport sentinel would be stored/compared as text and
                # breaks ordered predicates such as amount > Decimal("50").
                res.append(str(v._data))
            elif getattr(v, '_type_hint', None) == DataType.Json or isinstance(v._data, (dict, list)):
                res.append(json.dumps(v._data))
            elif getattr(v, '_type_hint', None) == DataType.Date or isinstance(v._data, date):
                if hasattr(v._data, "strftime"):
                    res.append(v._data.strftime("%Y-%m-%d"))
                else:
                    res.append(str(v._data))
            elif getattr(v, '_type_hint', None) == DataType.Timestamp or isinstance(v._data, Timestamp):
                if hasattr(v._data, "millis"):
                    res.append(v._data.millis)
                else:
                    res.append(int(v._data))
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
            await self._prepare(db)
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

    async def stream_sql(self, query: CompiledQuery, chunk_size: int) -> AsyncIterator[List[Dict[str, Any]]]:
        sql = query.sql_with_comment(); params = self._bind_values(query.params)
        is_uri = self.db_path.startswith("file:")
        async with aiosqlite.connect(self.db_path, uri=is_uri) as db:
            await self._prepare(db)
            db.row_factory = aiosqlite.Row
            async with db.execute(sql, params) as cursor:
                columns = [col[0] for col in cursor.description]
                while True:
                    rows = await cursor.fetchmany(chunk_size)
                    if not rows: break
                    yield [{name: self._decode_value(row[i]) for i, name in enumerate(columns)} for row in rows]

    async def execute_sql(self, query: CompiledQuery) -> tuple[int, int]:
        sql = query.sql_with_comment()
        params = self._bind_values(query.params)
        
        is_uri = self.db_path.startswith("file:")
        async with aiosqlite.connect(self.db_path, uri=is_uri) as db:
            await self._prepare(db)
            async with db.execute(sql, params) as cursor:
                await db.commit()
                return cursor.rowcount, cursor.lastrowid

    async def begin_sql(self) -> 'SqlTransactionTransportTx':
        is_uri = self.db_path.startswith("file:")
        db = await aiosqlite.connect(self.db_path, uri=is_uri)
        await self._prepare(db)
        await db.execute("BEGIN IMMEDIATE")
        return _SqliteTransaction(db, self._bind_values, self._decode_value)


class _SqliteTransaction(SqlTransactionTransportTx):
    def __init__(self, db, bind_values, decode_value):
        self.db = db
        self._bind_values = bind_values
        self._decode_value = decode_value

    async def fetch_all_sql(self, query: CompiledQuery) -> List[Dict[str, Any]]:
        self.db.row_factory = aiosqlite.Row
        async with self.db.execute(query.sql_with_comment(), self._bind_values(query.params)) as cursor:
            rows = await cursor.fetchall()
            if not rows:
                return []
            columns = [col[0] for col in cursor.description]
            return [
                {name: self._decode_value(row[index]) for index, name in enumerate(columns)}
                for row in rows
            ]

    async def execute_sql(self, query: CompiledQuery) -> tuple[int, int]:
        async with self.db.execute(query.sql_with_comment(), self._bind_values(query.params)) as cursor:
            return cursor.rowcount, cursor.lastrowid

    async def commit_sql(self) -> None:
        try:
            await self.db.commit()
        finally:
            await self.db.close()

    async def rollback_sql(self) -> None:
        try:
            await self.db.rollback()
        finally:
            await self.db.close()
