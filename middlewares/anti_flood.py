import time
from collections import defaultdict
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message

from config import FLOOD_THRESHOLD, FLOOD_WINDOW


class AntiFloodMiddleware(BaseMiddleware):
    def __init__(self, threshold: int = FLOOD_THRESHOLD, window: int = FLOOD_WINDOW):
        super().__init__()
        self.threshold = threshold
        self.window = window
        self.user_messages: Dict[int, list] = defaultdict(list)

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        if not event.text:
            return await handler(event, data)

        user_id = event.from_user.id
        now = time.time()

        self.user_messages[user_id] = [
            t for t in self.user_messages[user_id] if now - t < self.window
        ]

        if len(self.user_messages[user_id]) >= self.threshold:
            try:
                await event.delete()
            except Exception:
                pass

            if len(self.user_messages[user_id]) == self.threshold:
                await event.answer(
                    f"⚠️ {event.from_user.full_name} لطفاً آروم‌تر پیام بفرست.",
                    delete_after=5
                )

            self.user_messages[user_id].append(now)
            return None

        self.user_messages[user_id].append(now)
        return await handler(event, data)
