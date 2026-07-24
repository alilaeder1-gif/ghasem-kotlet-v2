import time
import logging
from database import db

logger = logging.getLogger(__name__)

_EMERGENCY = {"active": False, "reason": "", "started_at": 0}

_ERROR_COUNTS: list[tuple[float, str]] = []
_ERROR_WINDOW = 300
_ERROR_THRESHOLD = 0.3
_MIN_ERRORS = 10


def record_error(error_type: str = "api_timeout"):
    now = time.time()
    cutoff = now - _ERROR_WINDOW
    global _ERROR_COUNTS
    _ERROR_COUNTS = [(t, e) for t, e in _ERROR_COUNTS if t > cutoff]
    _ERROR_COUNTS.append((now, error_type))


def _error_rate() -> float:
    now = time.time()
    cutoff = now - _ERROR_WINDOW
    recent = [(t, e) for t, e in _ERROR_COUNTS if t > cutoff]
    if len(recent) < _MIN_ERRORS:
        return 0.0
    return len(recent) / _ERROR_WINDOW * 60


def _api_timeout_rate() -> float:
    now = time.time()
    cutoff = now - _ERROR_WINDOW
    timeouts = [(t, e) for t, e in _ERROR_COUNTS if t > cutoff and e == "api_timeout"]
    total = [(t, e) for t, e in _ERROR_COUNTS if t > cutoff]
    if not total:
        return 0.0
    return len(timeouts) / len(total)


async def check_emergency() -> dict:
    global _EMERGENCY
    if _EMERGENCY["active"]:
        since = time.time() - _EMERGENCY["started_at"]
        if since > 1800:
            _EMERGENCY = {"active": False, "reason": "", "started_at": 0}
            logger.info("Emergency mode auto-recovered after 30min")
        return dict(_EMERGENCY)

    reasons = []
    if _api_timeout_rate() > 0.5:
        reasons.append("API timeout rate > 50%")
    if _error_rate() > _ERROR_THRESHOLD:
        reasons.append(f"Error rate > {_ERROR_THRESHOLD*100}%")
    rate_limit_count = sum(1 for _, e in _ERROR_COUNTS if e == "rate_limit")
    if rate_limit_count > 10:
        reasons.append(f"Rate limit > 10 in window")

    if reasons:
        _EMERGENCY = {
            "active": True,
            "reason": "; ".join(reasons),
            "started_at": time.time(),
        }
        logger.warning(f"Emergency mode activated: {_EMERGENCY['reason']}")

    return dict(_EMERGENCY)


async def manual_set(active: bool, reason: str = ""):
    global _EMERGENCY
    _EMERGENCY = {
        "active": active,
        "reason": reason or ("دستوری" if active else ""),
        "started_at": time.time() if active else 0,
    }
    logger.info(f"Emergency mode {'ON' if active else 'OFF'}: {reason}")
    return dict(_EMERGENCY)


def is_emergency() -> bool:
    return _EMERGENCY["active"]


def get_emergency_status() -> dict:
    return dict(_EMERGENCY)
