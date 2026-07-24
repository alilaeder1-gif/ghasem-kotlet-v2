"""Idempotency — deduplicate Telegram updates using update_id in Redis.

Prevents duplicate processing when Telegram sends the same update twice.
"""
import logging
import time

logger = logging.getLogger(__name__)


class IdempotencyGuard:
    def __init__(self, ttl: int = 3600, prefix: str = "idem:"):
        self._ttl = ttl
        self._prefix = prefix
        self._local_cache: set[int] = set()

    async def _redis(self):
        try:
            from cache import cache
            if cache.enabled and cache.client:
                return cache.client
        except: pass
        return None

    async def is_processed(self, update_id: int) -> bool:
        """Check if update_id was already processed."""
        if update_id in self._local_cache:
            return True
        r = await self._redis()
        if r:
            try:
                exists = await r.exists(f"{self._prefix}{update_id}")
                if exists:
                    self._local_cache.add(update_id)
                    return True
            except: pass
        return False

    async def mark_processed(self, update_id: int):
        """Mark update_id as processed."""
        self._local_cache.add(update_id)
        if len(self._local_cache) > 10000:
            self._local_cache.clear()
        r = await self._redis()
        if r:
            try:
                await r.setex(f"{self._prefix}{update_id}", self._ttl, "1")
            except: pass


idempotency = IdempotencyGuard()
