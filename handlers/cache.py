import time
import logging

logger = logging.getLogger(__name__)


class MemoryCache:
    def __init__(self):
        self._store: dict[str, tuple[str, float]] = {}

    async def get(self, key: str) -> str | None:
        if key in self._store:
            val, expiry = self._store[key]
            if time.time() < expiry:
                return val
            del self._store[key]
        return None

    async def set(self, key: str, value: str, ttl: int = 3600):
        self._store[key] = (value, time.time() + ttl)

    async def delete(self, key: str):
        self._store.pop(key, None)

    async def clear(self):
        self._store.clear()


cache = MemoryCache()
