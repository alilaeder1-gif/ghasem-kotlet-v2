"""Feature Flags — DB-driven toggle for features, manageable from admin panel.

Usage:
    from handlers.feature_flags import feature_flags
    if await feature_flags.is_enabled("ai_chat"):
        await handle_ai_chat()
"""
import logging
from database import db

logger = logging.getLogger(__name__)

DEFAULT_FLAGS = {
    "ai_chat": True,
    "broadcast": True,
    "health_monitor": True,
    "ai_queue": True,
    "backup": True,
    "anti_spam": True,
    "anti_link": True,
    "anti_flood": True,
    "captcha": False,
    "welcome": True,
    "auto_delete": False,
}


class FeatureFlags:
    def __init__(self):
        self._cache: dict[str, bool] = {}
        self._loaded = False

    async def _load(self):
        if self._loaded:
            return
        for key, default in DEFAULT_FLAGS.items():
            try:
                val = await db.get_setting(f"flag_{key}", str(int(default)))
                self._cache[key] = val == "1"
            except:
                self._cache[key] = default
        self._loaded = True

    async def is_enabled(self, flag: str) -> bool:
        if not self._loaded:
            await self._load()
        return self._cache.get(flag, DEFAULT_FLAGS.get(flag, True))

    async def set_enabled(self, flag: str, enabled: bool):
        self._cache[flag] = enabled
        try:
            await db.set_setting(f"flag_{flag}", str(int(enabled)))
        except:
            pass

    async def toggle(self, flag: str) -> bool:
        current = await self.is_enabled(flag)
        await self.set_enabled(flag, not current)
        return not current

    def all_flags(self) -> dict[str, bool]:
        return dict(self._cache) if self._loaded else dict(DEFAULT_FLAGS)

    async def refresh(self):
        self._loaded = False
        await self._load()


feature_flags = FeatureFlags()
