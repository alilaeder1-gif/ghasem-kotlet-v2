import asyncio
import logging
import time
from datetime import datetime, timezone
from handlers.key_pool import gemini_pool, groq_pool, openrouter_pool

logger = logging.getLogger(__name__)
_INTERVAL = 1800


async def test_key(provider: str, api_key: str) -> bool:
    try:
        import requests
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        endpoints = {
            "gemini": ("https://generativelanguage.googleapis.com/v1beta/models?key=" + api_key, None),
            "groq": ("https://api.groq.com/openai/v1/chat/completions", {
                "model": "llama-3.1-8b-instant", "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5
            }),
            "openrouter": ("https://openrouter.ai/api/v1/chat/completions", {
                "model": "deepseek/deepseek-chat", "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5
            }),
        }
        if provider not in endpoints: return True
        url, data = endpoints[provider]
        if data:
            r = requests.post(url, headers=headers, json=data, timeout=15)
        else:
            r = requests.get(url, headers=headers, timeout=15)
        return r.status_code < 500
    except: return False


async def check_pool(pool, provider: str):
    for k in pool.keys:
        if not k.healthy and k.cooldown_until and time.time() < k.cooldown_until:
            cooldown_min = int((k.cooldown_until - time.time()) / 60)
            if cooldown_min > 5:
                continue
        if k.healthy:
            ok = await test_key(provider, k.key)
            if not ok:
                k.failures += 1
                if k.failures >= 3:
                    k.healthy = False
                    k.cooldown_until = time.time() + 600
                    logger.info(f"Scheduler: {provider} key ...{k.key[-4:]} marked dead")
        else:
            ok = await test_key(provider, k.key)
            if ok:
                k.healthy = True
                k.failures = 0
                k.cooldown_until = 0
                logger.info(f"Scheduler: {provider} key ...{k.key[-4:]} revived")
        if k.db_id:
            try:
                import asyncio as _a
                _a.ensure_future(pool._sync_to_db(k))
            except: pass


async def scheduled_health_check():
    while True:
        try:
            logger.info("Scheduler: running health check...")
            await check_pool(gemini_pool, "gemini")
            await check_pool(groq_pool, "groq")
            await check_pool(openrouter_pool, "openrouter")
            stats = {
                "gemini": gemini_pool.status(),
                "groq": groq_pool.status(),
                "openrouter": openrouter_pool.status(),
            }
            info = " | ".join(f"{n}: {s['healthy']}h/{s['cooldown']}c/{s['dead']}d" for n, s in stats.items())
            logger.info(f"Scheduler: done. {info}")
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        await asyncio.sleep(_INTERVAL)
