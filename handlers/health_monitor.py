import asyncio
import logging
import time
from datetime import datetime, timezone

from cache import cache
from database import db
from handlers.circuit_breaker import circuit_breaker

logger = logging.getLogger(__name__)

_INTERVAL = 600
_last_status: dict[str, str] = {}
_admin_alerted: set[str] = set()


async def _real_test_gemini() -> str:
    try:
        import google.generativeai as genai
        from handlers.key_pool import gemini_pool
        key = gemini_pool.get_key()
        if not key: return "no_keys"
        genai.configure(api_key=key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        resp = model.generate_content("سلام! چطوری؟ در یک جمله جواب بده.", generation_config={"max_output_tokens": 30})
        if resp and resp.text and len(resp.text) > 3:
            return "healthy"
        return "error:empty_response"
    except Exception as e:
        el = str(e).lower()
        if "429" in el or "quota" in el or "rate" in el: return "ratelimit"
        if "403" in el or "permission" in el or "api key" in el: return "unauthorized"
        if "deadline" in el or "timeout" in el or "unavailable" in el: return "timeout"
        return f"error:{str(e)[:60]}"


async def _real_test_groq() -> str:
    try:
        from handlers.key_pool import groq_pool
        key = groq_pool.get_key()
        if not key: return "no_keys"
        import requests
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": "سلام! چطوری؟ در یک جمله جواب بده."}],
                "max_tokens": 30,
            },
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            choices = data.get("choices", [])
            if choices and choices[0].get("message", {}).get("content", "").strip():
                return "healthy"
            return "error:empty_response"
        if r.status_code == 429: return "ratelimit"
        if r.status_code == 401: return "unauthorized"
        if r.status_code >= 500: return "timeout"
        return f"error:http_{r.status_code}"
    except Exception as e:
        el = str(e).lower()
        if "timeout" in el or "deadline" in el: return "timeout"
        return f"error:{str(e)[:60]}"


async def _real_test_openrouter() -> str:
    try:
        from handlers.key_pool import openrouter_pool
        key = openrouter_pool.get_key()
        if not key: return "no_keys"
        import requests
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/alilaeder1-gif/ghasem-kotlet-v2",
            },
            json={
                "model": "deepseek/deepseek-chat",
                "messages": [{"role": "user", "content": "سلام! چطوری؟ در یک جمله جواب بده."}],
                "max_tokens": 30,
            },
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            choices = data.get("choices", [])
            if choices and choices[0].get("message", {}).get("content", "").strip():
                return "healthy"
            return "error:empty_response"
        if r.status_code == 429: return "ratelimit"
        if r.status_code == 401: return "unauthorized"
        return f"error:http_{r.status_code}"
    except Exception as e:
        return f"error:{str(e)[:60]}"


async def check_redis() -> str:
    try:
        if not cache.enabled or not cache.client:
            return "disabled"
        await cache.client.ping()
        return "healthy"
    except Exception as e:
        return f"error:{str(e)[:40]}"


async def check_database() -> str:
    try:
        async with db.db.execute("SELECT 1") as c:
            await c.fetchone()
        return "healthy"
    except Exception as e:
        return f"error:{str(e)[:40]}"


async def check_telegram(bot) -> str:
    try:
        me = await bot.get_me()
        return "healthy" if me else "error:no_response"
    except Exception as e:
        return f"error:{str(e)[:40]}"


_STATUS_ICONS = {
    "healthy": "🟢", "ratelimit": "🟡", "unauthorized": "🔴",
    "no_keys": "⚪", "disabled": "⚪", "timeout": "🟠", "unknown": "🔵",
}
_STATUS_LABELS = {
    "healthy": "سالم", "ratelimit": "محدودیت", "unauthorized": "عدم دسترسی",
    "no_keys": "بدون کلید", "disabled": "غیرفعال", "timeout": "قطع ارتباط",
    "unknown": "نامشخص",
}


def _status_icon(st: str) -> str:
    base = st.split(":")[0]
    return _STATUS_ICONS.get(base, "❓")


def _status_label(st: str) -> str:
    base = st.split(":")[0]
    return _STATUS_LABELS.get(base, st)


async def run_health_check(bot) -> dict[str, str]:
    results = {}

    # Real AI tests with circuit breaker integration
    cb_gemini = circuit_breaker.get("gemini")
    if cb_gemini.allow_request():
        results["gemini"] = await _real_test_gemini()
        if results["gemini"] == "healthy":
            cb_gemini.record_success()
        else:
            cb_gemini.record_failure()
    else:
        results["gemini"] = "circuit_open"

    cb_groq = circuit_breaker.get("groq")
    if cb_groq.allow_request():
        results["groq"] = await _real_test_groq()
        if results["groq"] == "healthy":
            cb_groq.record_success()
        else:
            cb_groq.record_failure()
    else:
        results["groq"] = "circuit_open"

    cb_or = circuit_breaker.get("openrouter")
    if cb_or.allow_request():
        results["openrouter"] = await _real_test_openrouter()
        if results["openrouter"] == "healthy":
            cb_or.record_success()
        else:
            cb_or.record_failure()
    else:
        results["openrouter"] = "circuit_open"

    results["redis"] = await check_redis()
    results["database"] = await check_database()
    results["telegram"] = await check_telegram(bot)

    logger.info(f"Health: {' | '.join(f'{k}={v}' for k, v in results.items())}")
    try:
        from handlers.json_logger import json_logger
        json_logger.info("health_check", results=results)
    except: pass
    return results


def _build_alert_message(results: dict[str, str]) -> str:
    parts = ["🚨 **AI ALERT**\n"]
    for name, st in results.items():
        icon = _status_icon(st)
        label = _status_label(st)
        parts.append(f"{icon} {name}: {label}")
    now = datetime.now(timezone.utc).strftime("%H:%M UTC")
    parts.append(f"\n⏰ Time: {now}")

    # Circuit breaker summary
    cb_states = circuit_breaker.all_status()
    cb_lines = [f"{s['icon']} {n}: {s['state']}" for n, s in cb_states.items()]
    if cb_lines:
        parts.append(f"\n**Circuit Breakers:**")
        parts.extend(cb_lines)

    return "\n".join(parts)


def get_health_summary() -> dict:
    return dict(_last_status)


async def _do_health_check(bot):
    global _last_status, _admin_alerted
    results = await run_health_check(bot)
    _last_status = results

    from config import ADMIN_IDS
    admins = set(ADMIN_IDS)
    try:
        owners = await db.get_users_by_role("owner")
        admins.update(owners)
    except:
        pass

    unhealthy = {k: v for k, v in results.items()
                 if not v.startswith("healthy") and v not in ("disabled", "circuit_open")}
    healthy_now = {k for k, v in results.items()
                   if v.startswith("healthy") or v in ("disabled",)}

    if unhealthy:
        msg = _build_alert_message(unhealthy)
        for admin_id in admins:
            try:
                await bot.send_message(admin_id, msg)
                await asyncio.sleep(0.5)
            except:
                pass

    recovered = _admin_alerted & healthy_now
    if recovered:
        msg_parts = ["✅ **بازیابی سرویس**\n"]
        for name in recovered:
            msg_parts.append(f"🟢 {name}: سالم")
        msg_parts.append(f"\n⏰ {datetime.now(timezone.utc).strftime('%H:%M UTC')}")
        for admin_id in admins:
            try:
                await bot.send_message(admin_id, "\n".join(msg_parts))
                await asyncio.sleep(0.5)
            except:
                pass

    _admin_alerted = set(unhealthy.keys())

    try:
        for name, st in results.items():
            rtype = "success" if st == "healthy" else "failure"
            await db.log_health_check(name, rtype)
    except:
        pass


async def health_monitor_worker(bot):
    from handlers.distributed_lock import distributed_lock
    await asyncio.sleep(30)
    while True:
        try:
            locked = await distributed_lock.acquire("health_check", ttl=300)
            if not locked:
                logger.debug("Health: lock held by another replica, skipping")
            else:
                try:
                    await _do_health_check(bot)
                finally:
                    await distributed_lock.release("health_check")
        except Exception as e:
            logger.error(f"Health monitor error: {e}")
        await asyncio.sleep(_INTERVAL)
