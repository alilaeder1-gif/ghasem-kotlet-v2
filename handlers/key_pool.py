import time
import logging
from datetime import datetime, timezone
logger = logging.getLogger(__name__)

_COOLDOWN_429 = 600
_COOLDOWN_AUTH = 3600
_MAX_FAILURES = 3


class KeyStatus:
    def __init__(self, key: str, db_id: int = None, provider: str = ""):
        self.key = key
        self.db_id = db_id
        self.provider = provider
        self.healthy = True
        self.failures = 0
        self.cooldown_until = 0
        self.total_calls = 0
        self.last_error = ""
        self.last_used = 0

    def record_success(self):
        self.failures = 0
        self.total_calls += 1
        self.last_used = time.time()
        self.healthy = True
        self.cooldown_until = 0

    def record_failure(self, error_type: str):
        self.failures += 1
        self.last_error = error_type
        self.total_calls += 1
        now = time.time()
        if error_type == "rate_limit":
            self.cooldown_until = now + _COOLDOWN_429
            logger.info(f"Key ...{self.key[-4:]} rate limited, cooldown {_COOLDOWN_429}s")
        elif error_type == "auth_fail":
            self.cooldown_until = now + _COOLDOWN_AUTH
            self.healthy = False
            logger.warning(f"Key ...{self.key[-4:]} auth failed, cooldown {_COOLDOWN_AUTH}s")
        else:
            if self.failures >= _MAX_FAILURES:
                self.cooldown_until = now + 120
                logger.info(f"Key ...{self.key[-4:]} {self.failures} failures, cooldown 120s")
        if self.failures >= _MAX_FAILURES * 2:
            self.healthy = False

    def is_available(self) -> bool:
        if not self.healthy:
            return False
        if self.cooldown_until and time.time() < self.cooldown_until:
            return False
        return True

    def reset(self):
        self.healthy = True
        self.failures = 0
        self.cooldown_until = 0
        self.last_error = ""


class KeyPool:
    def __init__(self, name: str, keys: list[str] = None):
        self.name = name
        self.keys: list[KeyStatus] = [KeyStatus(k, provider=name) for k in (keys or []) if k]
        self._index = 0
        self._db_ready = False

    async def load_from_db(self):
        try:
            from database import db
            rows = await db.get_healthy_keys(self.name)
            self.keys = []
            for r in rows:
                ks = KeyStatus(r["api_key"], db_id=r["id"], provider=self.name)
                ks.total_calls = r.get("total_calls", 0)
                ks.health = r.get("health", 100.0)
                cooldown = r.get("cooldown_until")
                if cooldown:
                    try:
                        dt = datetime.fromisoformat(cooldown)
                        ks.cooldown_until = dt.timestamp()
                    except: pass
                self.keys.append(ks)
            self._db_ready = True
            logger.info(f"{self.name}: loaded {len(self.keys)} keys from DB")
        except Exception as e:
            logger.warning(f"{self.name}: DB load failed, using in-memory keys: {e}")

    async def _sync_to_db(self, ks: KeyStatus):
        if not self._db_ready or not ks.db_id:
            return
        try:
            from database import db
            cooldown_str = None
            if ks.cooldown_until:
                cooldown_str = datetime.fromtimestamp(ks.cooldown_until, tz=timezone.utc).isoformat()
            await db.update_key_status(
                ks.db_id,
                status="healthy" if ks.healthy else "dead",
                health=max(0, 100 - ks.failures * 20),
                cooldown_until=cooldown_str,
                requests_today=ks.total_calls,
                total_calls=ks.total_calls,
                last_error=ks.last_error or "",
            )
        except Exception as e:
            logger.debug(f"DB sync error for {self.name}: {e}")

    def get_key(self) -> str | None:
        available = [k for k in self.keys if k.is_available()]
        if not available:
            expired = [k for k in self.keys if not k.healthy and k.cooldown_until and time.time() >= k.cooldown_until]
            for k in expired:
                k.reset()
                available.append(k)
        if not available:
            logger.warning(f"{self.name}: no healthy keys available")
            return None
        self._index = self._index % len(available)
        key = available[self._index].key
        self._index = (self._index + 1) % len(available)
        return key

    def record_success(self, key: str):
        for k in self.keys:
            if k.key == key:
                k.record_success()
                import asyncio
                asyncio.ensure_future(self._sync_to_db(k))
                break

    def record_failure(self, key: str, error_type: str):
        for k in self.keys:
            if k.key == key:
                k.record_failure(error_type)
                import asyncio
                asyncio.ensure_future(self._sync_to_db(k))
                break

    def add_key(self, api_key: str, db_id: int = None):
        self.keys.append(KeyStatus(api_key, db_id=db_id, provider=self.name))

    def remove_key(self, index: int):
        if 0 <= index < len(self.keys):
            self.keys.pop(index)

    def status(self) -> dict:
        return {
            "name": self.name,
            "total": len(self.keys),
            "healthy": sum(1 for k in self.keys if k.is_available()),
            "cooldown": sum(1 for k in self.keys if k.cooldown_until and time.time() < k.cooldown_until),
            "dead": sum(1 for k in self.keys if not k.healthy),
            "total_calls": sum(k.total_calls for k in self.keys),
        }

    def get_key_by_index(self, index: int) -> KeyStatus | None:
        if 0 <= index < len(self.keys):
            return self.keys[index]
        return None


gemini_pool = KeyPool("gemini")
groq_pool = KeyPool("groq")
openrouter_pool = KeyPool("openrouter")


async def init_pools_from_db():
    for pool in [gemini_pool, groq_pool, openrouter_pool]:
        await pool.load_from_db()
    # Fallback: if DB empty, seed from env
    total = sum(len(p.keys) for p in [gemini_pool, groq_pool, openrouter_pool])
    if total == 0:
        logger.info("No keys in DB, seeding from env vars")
        from database import db
        await db.seed_api_keys_from_env()
        for pool in [gemini_pool, groq_pool, openrouter_pool]:
            await pool.load_from_db()


def classify_error(err_str: str) -> str:
    if any(k in err_str for k in ["429", "Rate limit", "Too Many Requests", "quota", "Quota"]):
        return "rate_limit"
    if any(k in err_str for k in ["401", "Invalid API Key", "Unauthorized", "Missing Auth", "API_KEY_INVALID", "API key not valid"]):
        return "auth_fail"
    if any(k in err_str for k in ["402", "Payment Required", "insufficient_quota"]):
        return "quota"
    return "unknown"


def get_pool(provider: str) -> KeyPool:
    return {"gemini": gemini_pool, "groq": groq_pool, "openrouter": openrouter_pool}.get(provider, gemini_pool)


def all_pools_status() -> dict:
    return {
        "gemini": gemini_pool.status(),
        "groq": groq_pool.status(),
        "openrouter": openrouter_pool.status(),
    }
