"""Async queue system for AI requests with optional Redis persistence.

Usage:
    from handlers.ai_queue import ai_queue
    result = await ai_queue.enqueue(user_id, priority, ai_coro)
    
Priorities:
    0 = VIP (fastest)
    1 = Normal
    2 = Low

Redis persistence:
    Set REDIS_QUEUE_ENABLED=true in env to persist pending items.
    On restart, queued items are restored from Redis.
"""
import asyncio
import json
import logging
import os
import time
from collections import deque

logger = logging.getLogger(__name__)


class PersistentQueue:
    def __init__(self, max_concurrent: int = 3, redis_prefix: str = "aiq:"):
        self._max_concurrent = max_concurrent
        self._redis_prefix = redis_prefix
        self._active = 0
        self._queues: dict[int, deque] = {0: deque(), 1: deque(), 2: deque()}
        self._pending_futures: dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()
        self._worker_task = None
        self._total_enqueued = 0
        self._total_processed = 0
        self._total_failed = 0
        self._wait_times: list[float] = []
        self._redis_enabled = os.environ.get("REDIS_QUEUE_ENABLED", "").lower() in ("1", "true", "yes")

    async def _get_redis(self):
        try:
            from cache import cache
            if cache.enabled and cache.client:
                return cache.client
        except: pass
        return None

    async def start(self):
        if self._worker_task is not None:
            return

        # Restore from Redis if available
        if self._redis_enabled:
            restored = await self._restore_from_redis()
            if restored > 0:
                logger.info(f"AI Queue: restored {restored} items from Redis")

        self._worker_task = asyncio.create_task(self._worker())
        logger.info(f"AI Queue: started (max_concurrent={self._max_concurrent}, redis={self._redis_enabled})")

    async def stop(self):
        if self._worker_task:
            self._worker_task.cancel()
            self._worker_task = None

    async def enqueue(self, user_id: int, priority: int, coro) -> any:
        priority = max(0, min(2, priority))
        future = asyncio.Future()
        item = {
            "user_id": user_id,
            "coro": coro,
            "future": future,
            "enqueued_at": time.time(),
            "priority": priority,
        }
        item_id = f"{int(time.time() * 1000000)}_{user_id}"

        async with self._lock:
            self._queues[priority].append(item)
            self._pending_futures[item_id] = future
            self._total_enqueued += 1

        # Persist to Redis
        if self._redis_enabled:
            r = await self._get_redis()
            if r:
                try:
                    payload = json.dumps({
                        "id": item_id,
                        "user_id": user_id,
                        "priority": priority,
                        "enqueued_at": item["enqueued_at"],
                    })
                    await r.rpush(f"{self._redis_prefix}pending", payload)
                    await r.expire(f"{self._redis_prefix}pending", 86400)
                except: pass

        return await future

    async def _restore_from_redis(self) -> int:
        r = await self._get_redis()
        if not r:
            return 0
        restored = 0
        try:
            while True:
                payload = await r.lpop(f"{self._redis_prefix}pending")
                if not payload:
                    break
                try:
                    data = json.loads(payload)
                    prio = data.get("priority", 1)
                    uid = data.get("user_id", 0)
                    # Create a no-op coro, user will get timeout
                    async def _noop():
                        return "⏳ درخواست شما در صف باقی ماند و پس از ری‌استارت از دست رفت. لطفاً دوباره بپرسید."
                    future = asyncio.Future()
                    self._queues[prio].append({
                        "user_id": uid,
                        "coro": _noop(),
                        "future": future,
                        "enqueued_at": data.get("enqueued_at", time.time()),
                        "priority": prio,
                    })
                    restored += 1
                except: pass
        except: pass
        return restored

    async def _worker(self):
        while True:
            try:
                has_work = False
                async with self._lock:
                    if self._active < self._max_concurrent:
                        for prio in [0, 1, 2]:
                            if self._queues[prio]:
                                item = self._queues[prio].popleft()
                                has_work = True
                                break

                if has_work:
                    self._active += 1
                    asyncio.create_task(self._process(item))
                else:
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"AI Queue worker error: {e}")
                await asyncio.sleep(1)

    async def _process(self, item: dict):
        try:
            wait_time = time.time() - item["enqueued_at"]
            self._wait_times.append(wait_time)
            if len(self._wait_times) > 100:
                self._wait_times = self._wait_times[-100:]

            result = await item["coro"]
            item["future"].set_result(result)
            self._total_processed += 1
        except Exception as e:
            self._total_failed += 1
            if not item["future"].done():
                item["future"].set_exception(e)
        finally:
            self._active -= 1

    def stats(self) -> dict:
        avg_wait = sum(self._wait_times) / len(self._wait_times) if self._wait_times else 0
        return {
            "active": self._active,
            "queued": sum(len(q) for q in self._queues.values()),
            "queued_detail": {str(k): len(v) for k, v in self._queues.items()},
            "processed": self._total_processed,
            "failed": self._total_failed,
            "avg_wait_sec": round(avg_wait, 2),
            "max_concurrent": self._max_concurrent,
            "redis_enabled": self._redis_enabled,
        }


ai_queue = PersistentQueue(max_concurrent=3)
