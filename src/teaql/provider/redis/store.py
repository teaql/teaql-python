import json
from typing import Optional
import redis.asyncio as redis
from teaql.core.value import Value
from teaql.runtime.store import DataStore

class RedisDataStore(DataStore):
    def __init__(self, redis_url: str):
        """
        Creates a new Redis data store.
        URL format: redis://[<username>][:<password>@]<hostname>[:port][/<db>]
        """
        self.redis_url = redis_url
        self._pool = redis.ConnectionPool.from_url(redis_url)
        self.client = redis.Redis.from_pool(self._pool)

    async def get(self, key: str) -> Optional[Value]:
        json_str = await self.client.get(key)
        if json_str is not None:
            try:
                json_value = json.loads(json_str)
                return Value.from_json(json_value)
            except json.JSONDecodeError:
                pass
        return None

    async def put(self, key: str, value: Value, timeout_seconds: Optional[int] = None) -> None:
        try:
            # Need to convert Value to a dict/list equivalent
            # Assuming value has a `to_json_value` or we just serialize _data if it's Json
            if getattr(value, 'to_json_value', None):
                json_value = value.to_json_value()
            else:
                json_value = value._data
                
            json_str = json.dumps(json_value)
            
            if timeout_seconds is not None:
                await self.client.setex(key, timeout_seconds, json_str)
            else:
                await self.client.set(key, json_str)
        except Exception:
            pass

    async def remove(self, key: str) -> None:
        await self.client.delete(key)
        
    async def close(self):
        await self.client.aclose()
        await self._pool.disconnect()
