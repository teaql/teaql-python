from typing import Optional
import json
from teaql.core.value import Value

class DataStore:
    async def get(self, key: str) -> Optional[Value]:
        raise NotImplementedError

    async def put(self, key: str, value: Value, timeout_seconds: Optional[int] = None) -> None:
        raise NotImplementedError

    async def remove(self, key: str) -> None:
        raise NotImplementedError
