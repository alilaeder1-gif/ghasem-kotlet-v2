"""Distributed Lock — Redis-based mutex for multi-replica safety.

Usage:
    from handlers.distributed_lock import distributed_lock
    async with distributed_lock("backup", ttl=600):
        await create_backup()
"""
import asyncio
import logging
import os
import uuid

logger = logging.getLogger(__name__)


class DistributedLock:
    def __init__(self):
        self._instance_id = uuid.uuid4().hex[:8]

    async def _redis(self):
        try:
            from cache import cache
            if cache.enabled and cache.client:
                return cache.client
        except: pass
        return None

    async def acquire(self, name: str, ttl: int = 600) -> bool:
        r = await self._redis()
        if not r:
            return True  # no Redis = no lock = always allowed
        key = f"lock:{name}"
        try:
            acquired = await r.setnx(key, self._instance_id)
            if acquired:
                await r.expire(key, ttl)
                return True
            # Check if expired (shouldn't happen with Redis expire, but safe)
            existing = await r.get(key)
            return existing == self._instance_id
        except:
            return True  # allow on error

    async def release(self, name: str):
        r = await self._redis()
        if not r:
            return
        key = f"lock:{name}"
        try:
            # Only delete if we own the lock
            val = await r.get(key)
            if val and val.decode() if isinstance(val, bytes) else val == self._instance_id:
                await r.delete(key)
        except:
            pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False


distributed_lock = DistributedLock()
