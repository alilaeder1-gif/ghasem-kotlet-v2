import json
import hashlib
import logging
from config import REDIS_URL, REDIS_ENABLED

logger = logging.getLogger(__name__)

REDIS_AVAILABLE = False
try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except:
    try:
        from redis import asyncio as aioredis
        REDIS_AVAILABLE = True
    except:
        pass


class Cache:
    def __init__(self):
        self.client = None
        self.enabled = REDIS_ENABLED and REDIS_AVAILABLE

    async def connect(self):
        if not REDIS_URL or not REDIS_AVAILABLE:
            self.enabled = False
            return
        try:
            kwargs = {
                "decode_responses": True,
                "socket_connect_timeout": 5,
                "socket_timeout": 5,
                "retry_on_timeout": True,
                "health_check_interval": 30,
            }
            if REDIS_URL.startswith("rediss://"):
                kwargs["ssl_cert_reqs"] = None
            self.client = aioredis.from_url(REDIS_URL, **kwargs)
            await self.client.ping()
            self.enabled = True
        except:
            self.enabled = False
            self.client = None

    async def close(self):
        if self.client:
            try:
                await self.client.close()
            except:
                pass

    async def get(self, key: str) -> str | None:
        if not self.enabled or not self.client:
            return None
        try:
            return await self.client.get(key)
        except:
            return None

    async def set(self, key: str, value: str, ttl: int = 300):
        if not self.enabled or not self.client:
            return
        try:
            await self.client.set(key, value, ex=ttl)
        except:
            pass

    async def delete(self, key: str):
        if not self.enabled or not self.client:
            return
        try:
            await self.client.delete(key)
        except:
            pass

    async def remember(self, key: str, ttl: int = 300) -> str | None:
        if not self.enabled:
            return None
        return await self.get(key)

    async def cache_ai_response(self, message: str, system_prompt: str, response: str):
        key = f'ai:{hashlib.md5((message + system_prompt).encode()).hexdigest()}'
        await self.set(key, response, ttl=3600)

    async def get_ai_response(self, message: str, system_prompt: str) -> str | None:
        key = f'ai:{hashlib.md5((message + system_prompt).encode()).hexdigest()}'
        return await self.get(key)

    async def cache_group_settings(self, chat_id: int, data: dict):
        await self.set(f'gs:{chat_id}', json.dumps(data), ttl=60)

    async def get_group_settings(self, chat_id: int) -> dict | None:
        data = await self.get(f'gs:{chat_id}')
        return json.loads(data) if data else None

    async def check_rate_limit(self, key: str, limit: int = 5, window: int = 10) -> bool:
        if not self.enabled:
            return True
        try:
            current = await self.client.get(f'rl:{key}')
            if current and int(current) >= limit:
                return False
            await self.client.incr(f'rl:{key}')
            await self.client.expire(f'rl:{key}', window)
            return True
        except:
            return True


cache = Cache()
