import time
import logging
from config import GROQ_KEYS, GEMINI_KEYS, OPENROUTER_KEYS

logger = logging.getLogger(__name__)

_COOLDOWN_429 = 600
_COOLDOWN_AUTH = 3600
_MAX_FAILURES = 3


class KeyStatus:
    def __init__(self, key: str):
        self.key = key
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
    def __init__(self, name: str, keys: list[str]):
        self.name = name
        self.keys = [KeyStatus(k) for k in keys if k]
        self._index = 0

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
                break

    def record_failure(self, key: str, error_type: str):
        for k in self.keys:
            if k.key == key:
                k.record_failure(error_type)
                break

    def status(self) -> dict:
        return {
            "name": self.name,
            "total": len(self.keys),
            "healthy": sum(1 for k in self.keys if k.is_available()),
            "cooldown": sum(1 for k in self.keys if k.cooldown_until and time.time() < k.cooldown_until),
            "dead": sum(1 for k in self.keys if not k.healthy),
            "total_calls": sum(k.total_calls for k in self.keys),
        }


gemini_pool = KeyPool("gemini", GEMINI_KEYS)
groq_pool = KeyPool("groq", GROQ_KEYS)
openrouter_pool = KeyPool("openrouter", OPENROUTER_KEYS)


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
