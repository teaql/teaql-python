import json
import asyncpg
from decimal import Decimal
from datetime import date, datetime, timezone
from typing import List, Dict, Any, Optional, AsyncIterator
from teaql.sql.executor import SqlTransactionTransport, SqlTransactionTransportTx
from teaql.sql.types import CompiledQuery
from teaql.core.value import Value, DataType, Timestamp

class PostgresTransport(SqlTransactionTransport):
    def __init__(self, db_url: str):
        self.db_url = db_url

    def _bind_values(self, params: List[Value]) -> tuple:
        res = []
        for v in params:
            if v._data is None:
                res.append(None)
            elif getattr(v, '_type_hint', None) == DataType.Json or isinstance(v._data, (dict, list)):
                res.append(json.dumps(v._data))
            elif getattr(v, '_type_hint', None) == DataType.Timestamp or isinstance(v._data, Timestamp):
                if hasattr(v._data, "millis"):
                    res.append(datetime.fromtimestamp(v._data.millis / 1000.0, tz=timezone.utc))
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
        
        conn = await asyncpg.connect(self.db_url)
        try:
            rows = await conn.fetch(sql, *params)
            results = []
            for row in rows:
                record = {}
                for key, val in row.items():
                    record[key] = self._decode_value(val)
                results.append(record)
            return results
        finally:
            await conn.close()

    async def stream_sql(self, query: CompiledQuery, chunk_size: int) -> AsyncIterator[List[Dict[str, Any]]]:
        conn = await asyncpg.connect(self.db_url)
        transaction = conn.transaction()
        await transaction.start()
        try:
            cursor = conn.cursor(query.sql_with_comment(), *self._bind_values(query.params), prefetch=chunk_size)
            chunk = []
            async for row in cursor:
                chunk.append({key: self._decode_value(val) for key, val in row.items()})
                if len(chunk) == chunk_size:
                    yield chunk; chunk = []
            if chunk: yield chunk
        finally:
            await transaction.rollback()
            await conn.close()

    async def execute_sql(self, query: CompiledQuery) -> tuple[int, int]:
        sql = query.sql_with_comment()
        params = self._bind_values(query.params)
        
        conn = await asyncpg.connect(self.db_url)
        try:
            status = await conn.execute(sql, *params)
            # status typically like 'INSERT 0 1' or 'UPDATE 1'
            affected_rows = 0
            if status.startswith("UPDATE ") or status.startswith("DELETE "):
                affected_rows = int(status.split(" ")[1])
            elif status.startswith("INSERT "):
                affected_rows = int(status.split(" ")[2])
            return affected_rows, 0
        finally:
            await conn.close()

    async def begin_sql(self) -> SqlTransactionTransportTx:
        conn = await asyncpg.connect(self.db_url)
        try:
            transaction = conn.transaction()
            await transaction.start()
            return _PostgresTransaction(conn, transaction, self)
        except BaseException:
            await conn.close()
            raise


class _PostgresTransaction(SqlTransactionTransportTx):
    def __init__(self, conn, transaction, owner: PostgresTransport):
        self._conn = conn
        self._transaction = transaction
        self._owner = owner

    async def fetch_all_sql(self, query: CompiledQuery) -> List[Dict[str, Any]]:
        rows = await self._conn.fetch(query.sql_with_comment(), *self._owner._bind_values(query.params))
        return [
            {key: self._owner._decode_value(value) for key, value in row.items()}
            for row in rows
        ]

    async def execute_sql(self, query: CompiledQuery) -> tuple[int, int]:
        status = await self._conn.execute(query.sql_with_comment(), *self._owner._bind_values(query.params))
        if status.startswith("INSERT "):
            return int(status.split()[-1]), 0
        if status.startswith(("UPDATE ", "DELETE ")):
            return int(status.split()[-1]), 0
        return 0, 0

    async def commit_sql(self) -> None:
        try:
            await self._transaction.commit()
        finally:
            await self._conn.close()

    async def rollback_sql(self) -> None:
        try:
            await self._transaction.rollback()
        finally:
            await self._conn.close()
