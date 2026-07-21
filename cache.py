import json
import hashlib
from config import REDIS_URL, REDIS_ENABLED

try:
    import redis.asyncio as aioredis
except:
    REDIS_ENABLED = False


class Cache:
    def __init__(self):
        self.client = None
        self.enabled = REDIS_ENABLED

    async def connect(self):
        if not self.enabled or not REDIS_URL:
            self.enabled = False
            return
        try:
            self.client = aioredis.from_url(
                REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
            )
            await self.client.ping()
        except:
            self.enabled = False
            self.client = None

    async def close(self):
        if self.client:
            await self.client.close()

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
