"""Circuit Breaker pattern for AI providers.

States:
    CLOSED   — normal operation, requests pass through
    OPEN     — failing, requests blocked immediately (no pointless API calls)
    HALF_OPEN — one test request allowed; success → CLOSED, failure → OPEN

Usage:
    from handlers.circuit_breaker import circuit_breaker
    async with circuit_breaker("gemini"):
        response = await call_gemini(...)
"""
import asyncio
import logging
import time

logger = logging.getLogger(__name__)

# States
CLOSED = "CLOSED"
OPEN = "OPEN"
HALF_OPEN = "HALF_OPEN"

DEFAULT_FAILURE_THRESHOLD = 3
DEFAULT_TIMEOUT = 300  # 5 min in OPEN state
DEFAULT_HALF_OPEN_TIMEOUT = 30  # wait 30s before HALF_OPEN retry


class CircuitBreakerState:
    def __init__(self, name: str, failure_threshold: int = DEFAULT_FAILURE_THRESHOLD, timeout: int = DEFAULT_TIMEOUT):
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.state = CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self.last_success_time = 0
        self.total_failures = 0
        self.total_successes = 0
        self._half_open_lock = asyncio.Lock()

    def allow_request(self) -> bool:
        now = time.time()
        if self.state == CLOSED:
            return True
        if self.state == OPEN:
            if now - self.last_failure_time >= self.timeout:
                self.state = HALF_OPEN
                logger.info(f"Circuit [{self.name}]: OPEN → HALF_OPEN (timeout expired)")
                return True
            return False
        # HALF_OPEN: only allow one request
        return True

    def record_success(self):
        self.state = CLOSED
        self.failure_count = 0
        self.total_successes += 1
        self.last_success_time = time.time()
        logger.info(f"Circuit [{self.name}]: → CLOSED (success)")

    def record_failure(self):
        self.failure_count += 1
        self.total_failures += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold or self.state == HALF_OPEN:
            self.state = OPEN
            logger.warning(f"Circuit [{self.name}]: → OPEN ({self.failure_count} failures)")
        else:
            logger.debug(f"Circuit [{self.name}]: failure {self.failure_count}/{self.failure_threshold}")

    def reset(self):
        self.state = CLOSED
        self.failure_count = 0

    def status(self) -> dict:
        state_icon = {"CLOSED": "🟢", "OPEN": "🔴", "HALF_OPEN": "🟡"}
        return {
            "state": self.state,
            "icon": state_icon.get(self.state, "❓"),
            "failures": self.failure_count,
            "threshold": self.failure_threshold,
            "total_ok": self.total_successes,
            "total_fail": self.total_failures,
        }


class CircuitBreakerRegistry:
    def __init__(self):
        self._breakers: dict[str, CircuitBreakerState] = {}

    def get(self, name: str) -> CircuitBreakerState:
        if name not in self._breakers:
            self._breakers[name] = CircuitBreakerState(name)
        return self._breakers[name]

    def all_status(self) -> dict[str, dict]:
        return {n: b.status() for n, b in self._breakers.items()}


circuit_breaker = CircuitBreakerRegistry()


class CircuitBreakerContext:
    def __init__(self, name: str):
        self.name = name
        self._breaker = circuit_breaker.get(name)

    async def __aenter__(self):
        if not self._breaker.allow_request():
            raise CircuitBreakerOpenError(f"Circuit [{self.name}] is OPEN")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._breaker.record_success()
        elif exc_type is CircuitBreakerOpenError:
            pass  # was already blocked, no need to record
        else:
            self._breaker.record_failure()
        return False


class CircuitBreakerOpenError(Exception):
    pass


async def cb_call(name: str, coro):
    """Wrapper: call coro with circuit breaker protection."""
    breaker = circuit_breaker.get(name)
    if not breaker.allow_request():
        raise CircuitBreakerOpenError(f"Circuit [{name}] is OPEN")
    try:
        result = await coro
        breaker.record_success()
        return result
    except Exception as e:
        breaker.record_failure()
        raise
