"""Rate Limiter — per-user request throttling for AI Queue.

Prevents a single user from flooding the queue.
Uses Redis sliding window. Falls back to in-memory.
"""
import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self, default_max_requests: int = 30, default_window: int = 60):
        self._default_max = default_max_requests
        self._default_window = default_window
        self._local: dict[int, list[float]] = {}

    async def _redis(self):
        try:
            from cache import cache
            if cache.enabled and cache.client:
                return cache.client
        except: pass
        return None

    async def check(self, user_id: int, max_requests: int = None, window: int = None) -> tuple[bool, int]:
        """Returns (allowed, remaining_in_window)."""
        max_r = max_requests or self._default_max
        win = window or self._default_window
        now = time.time()

        # Try Redis first
        r = await self._redis()
        if r:
            try:
                key = f"ratelimit:{user_id}"
                pipe = r.pipeline()
                pipe.zremrangebyscore(key, 0, now - win)
                pipe.zcard(key)
                pipe.zadd(key, {str(now): now})
                pipe.expire(key, win)
                results = await pipe.execute()
                count = results[1]
                remaining = max(0, max_r - count)
                return count < max_r, remaining
            except:
                pass

        # Fallback: in-memory sliding window
        now_float = now
        if user_id not in self._local:
            self._local[user_id] = []
        timestamps = self._local[user_id]
        # Remove old entries
        cutoff = now_float - win
        self._local[user_id] = [t for t in timestamps if t > cutoff]
        count = len(self._local[user_id])
        if count < max_r:
            self._local[user_id].append(now_float)
            remaining = max_r - count - 1
            return True, remaining
        return False, 0

    async def get_remaining(self, user_id: int, max_requests: int = None, window: int = None) -> int:
        max_r = max_requests or self._default_max
        win = window or self._default_window
        now = time.time()
        r = await self._redis()
        if r:
            try:
                key = f"ratelimit:{user_id}"
                count = await r.zcard(key)
                return max(0, max_r - count)
            except: pass
        timestamps = [t for t in self._local.get(user_id, []) if t > now - win]
        return max(0, max_r - len(timestamps))


rate_limiter = RateLimiter(default_max_requests=30, default_window=60)
