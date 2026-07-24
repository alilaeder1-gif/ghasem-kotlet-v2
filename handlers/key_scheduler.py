import asyncio
import logging
import time
from datetime import datetime, timezone
from handlers.key_pool import gemini_pool, groq_pool, openrouter_pool

logger = logging.getLogger(__name__)
_INTERVAL = 300

# In-memory provider status cache
_provider_status: dict[str, str] = {}  # name -> "healthy" | "ratelimit" | "dead" | "unknown"


def get_provider_status() -> dict[str, str]:
    return dict(_provider_status)


async def test_key(provider: str, api_key: str) -> tuple[bool, str]:
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
            "cerebras": ("https://api.cerebras.ai/v1/chat/completions", {
                "model": "llama3.1-8b", "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5
            }),
            "sambanova": ("https://api.sambanova.ai/v1/chat/completions", {
                "model": "Meta-Llama-3.1-8B-Instruct", "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5
            }),
            "deepinfra": ("https://api.deepinfra.com/v1/openai/chat/completions", {
                "model": "meta-llama/Meta-Llama-3.1-8B-Instruct", "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5
            }),
        }
        if provider not in endpoints: return True, "unknown"
        url, data = endpoints[provider]
        if data:
            r = requests.post(url, headers=headers, json=data, timeout=15)
        else:
            r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 429:
            return False, "ratelimit"
        return r.status_code < 500, "healthy" if r.status_code < 500 else "dead"
    except requests.exceptions.Timeout:
        return False, "timeout"
    except Exception as e:
        return False, f"error:{str(e)[:30]}"


async def check_pool(pool, provider: str) -> str:
    overall = "unknown"
    for k in pool.keys:
        if not k.healthy and k.cooldown_until and time.time() < k.cooldown_until:
            cooldown_min = int((k.cooldown_until - time.time()) / 60)
            if cooldown_min > 5:
                continue
        if k.healthy:
            ok, status = await test_key(provider, k.key)
            if not ok:
                k.failures += 1
                if k.failures >= 3:
                    k.healthy = False
                    k.cooldown_until = time.time() + 600
                    logger.info(f"Scheduler: {provider} key ...{k.key[-4:]} marked dead ({status})")
                overall = status
            else:
                overall = "healthy"
        else:
            ok, status = await test_key(provider, k.key)
            if ok:
                k.healthy = True
                k.failures = 0
                k.cooldown_until = 0
                logger.info(f"Scheduler: {provider} key ...{k.key[-4:]} revived")
                overall = "healthy"
            else:
                if overall == "unknown":
                    overall = status
        if k.db_id:
            try:
                import asyncio as _a
                _a.ensure_future(pool._sync_to_db(k))
            except: pass
    if not pool.keys:
        overall = "no_keys"
    _provider_status[provider] = overall
    return overall


async def scheduled_health_check():
    while True:
        try:
            logger.info("Scheduler: running health check...")
            await check_pool(gemini_pool, "gemini")
            await check_pool(groq_pool, "groq")
            await check_pool(openrouter_pool, "openrouter")
            # test all known providers even without keys (shows status)
            from database import db
            all_provs = ["cerebras", "sambanova", "cloudflare", "deepinfra"]
            for p in all_provs:
                if p not in _provider_status:
                    keys = await db.get_all_keys(p)
                    if not keys:
                        _provider_status[p] = "no_keys"
                    else:
                        # test via their pools if loaded
                        pool_map = {}
                        if hasattr(p, "keys") and p in globals():
                            pool_map[p] = globals()[p]
                        _provider_status[p] = "unknown"

            status_icons = {"healthy": "🟢", "ratelimit": "🟡", "dead": "🔴", "no_keys": "⚪", "unknown": "🔵", "timeout": "🟠"}
            parts = []
            for prov, st in sorted(_provider_status.items()):
                icon = status_icons.get(st, "❓")
                parts.append(f"{icon} {prov}")
            logger.info(f"Scheduler: done. {' | '.join(parts)}")
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        await asyncio.sleep(_INTERVAL)
