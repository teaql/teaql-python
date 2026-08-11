import json
import time
from typing import Any, Optional
import redis

class RedisRemoteCacheProvider:
    def __init__(self, redis_url: str):
        self._pool = redis.ConnectionPool.from_url(redis_url)
        self.client = redis.Redis(connection_pool=self._pool)

    def put_to_remote_cache(self, key: str, value: Any, time_to_live_in_seconds: Optional[int] = None):
        try:
            json_str = json.dumps(value)
            if time_to_live_in_seconds is not None and time_to_live_in_seconds > 0:
                self.client.setex(key, time_to_live_in_seconds, json_str)
            else:
                self.client.set(key, json_str)
        except Exception:
            pass

    def get_from_remote_cache(self, key: str, clazz: Any = None) -> Optional[Any]:
        try:
            json_str = self.client.get(key)
            if json_str is not None:
                return json.loads(json_str)
        except Exception:
            pass
        return None

    def remove_from_remote_cache(self, key: str):
        try:
            self.client.delete(key)
        except Exception:
            pass

class RedisRemoteLockProvider:
    def __init__(self, redis_url: str):
        self._pool = redis.ConnectionPool.from_url(redis_url)
        self.client = redis.Redis(connection_pool=self._pool)

    def try_remote_lock(self, key: str, timeout_millis: int, expire_millis: int) -> bool:
        start = time.time() * 1000
        try:
            while True:
                if self.client.set(key, "locked", nx=True, px=expire_millis):
                    return True
                if (time.time() * 1000 - start) > timeout_millis:
                    return False
                time.sleep(0.01)
        except Exception:
            return False

    def unlock_remote(self, key: str):
        try:
            self.client.delete(key)
        except Exception:
            pass
