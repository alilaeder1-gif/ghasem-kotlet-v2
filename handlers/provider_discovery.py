"""Auto Provider Discovery — nightly scan of all available AI providers.

Tests every known provider endpoint. If a provider responds healthy,
it's added to the key pool (or marked as available if keys exist).
"""
import asyncio
import logging
import time

from database import db

logger = logging.getLogger(__name__)

# Known provider test endpoints
_PROVIDERS = {
    "gemini": {
        "test": lambda key: f"https://generativelanguage.googleapis.com/v1beta/models?key={key}",
        "type": "get",
        "success_codes": [200],
    },
    "groq": {
        "test": "https://api.groq.com/openai/v1/chat/completions",
        "type": "post",
        "data": {"model": "llama-3.1-8b-instant", "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5},
        "success_codes": [200],
    },
    "openrouter": {
        "test": "https://openrouter.ai/api/v1/auth/key",
        "type": "get",
        "success_codes": [200],
    },
    "cerebras": {
        "test": "https://api.cerebras.ai/v1/chat/completions",
        "type": "post",
        "data": {"model": "llama3.1-8b", "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5},
        "success_codes": [200],
    },
    "sambanova": {
        "test": "https://api.sambanova.ai/v1/chat/completions",
        "type": "post",
        "data": {"model": "Meta-Llama-3.1-8B-Instruct", "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5},
        "success_codes": [200],
    },
    "deepinfra": {
        "test": "https://api.deepinfra.com/v1/openai/chat/completions",
        "type": "post",
        "data": {"model": "meta-llama/Meta-Llama-3.1-8B-Instruct", "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5},
        "success_codes": [200],
    },
    "together": {
        "test": "https://api.together.xyz/v1/chat/completions",
        "type": "post",
        "data": {"model": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo", "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5},
        "success_codes": [200],
    },
    "fireworks": {
        "test": "https://api.fireworks.ai/inference/v1/chat/completions",
        "type": "post",
        "data": {"model": "accounts/fireworks/models/llama-v3p1-8b-instruct", "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5},
        "success_codes": [200],
    },
    "nebius": {
        "test": "https://api.nebius.ai/v1/chat/completions",
        "type": "post",
        "data": {"model": "meta-llama/Meta-Llama-3.1-8B-Instruct", "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5},
        "success_codes": [200],
    },
    "hyperbolic": {
        "test": "https://api.hyperbolic.xyz/v1/chat/completions",
        "type": "post",
        "data": {"model": "meta-llama/Meta-Llama-3.1-8B-Instruct", "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5},
        "success_codes": [200],
    },
}


async def _test_provider(provider: str, api_key: str) -> tuple[bool, float]:
    import requests
    info = _PROVIDERS.get(provider)
    if not info:
        return False, 0
    t0 = time.time()
    try:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        url = info["test"](api_key) if callable(info["test"]) else info["test"]

        if info["type"] == "post":
            r = requests.post(url, headers=headers, json=info.get("data", {}), timeout=10)
        else:
            r = requests.get(url, headers=headers, timeout=10)

        ok = r.status_code in info.get("success_codes", [200])
        return ok, time.time() - t0
    except:
        return False, time.time() - t0


async def discover_providers() -> dict[str, bool]:
    """Test all known providers. Returns {provider: is_healthy}."""
    results = {}
    all_keys = await db.get_all_keys()

    for provider in _PROVIDERS:
        # Find a key for this provider
        key_entry = next((k for k in all_keys if k.get("provider", "") == provider), None)
        if not key_entry:
            # Check if any key in the DB has this provider
            keys_for_prov = [k for k in all_keys if k.get("provider") == provider]
            if not keys_for_prov:
                # Check if provider exists in providers table
                pid = await db.get_provider_id(provider)
                if pid:
                    # Get keys for this provider
                    prov_keys = await db.get_all_keys(provider)
                    if prov_keys:
                        key_entry = prov_keys[0]

        if not key_entry:
            results[provider] = False
            continue

        ok, latency = await _test_provider(provider, key_entry["api_key"])
        results[provider] = ok
        if ok:
            logger.info(f"Discovery: {provider} is HEALTHY ({latency*1000:.0f}ms)")

    return results


async def discovery_worker():
    """Nightly auto-discovery of AI providers."""
    await asyncio.sleep(600)  # wait 10 min after bot start
    while True:
        try:
            logger.info("Discovery: scanning all providers...")
            results = await discover_providers()
            healthy = [p for p, ok in results.items() if ok]
            logger.info(f"Discovery: {len(healthy)}/{len(results)} healthy: {', '.join(healthy)}")

            # Auto-add healthy providers to DB if not already
            for provider in healthy:
                pid = await db.get_provider_id(provider)
                if not pid:
                    try:
                        await db.db.execute("INSERT INTO providers (name) VALUES (?)", (provider,))
                        await db.db.commit()
                        logger.info(f"Discovery: added {provider} to providers table")
                    except:
                        pass
        except Exception as e:
            logger.error(f"Discovery error: {e}")

        await asyncio.sleep(86400)  # 24h
