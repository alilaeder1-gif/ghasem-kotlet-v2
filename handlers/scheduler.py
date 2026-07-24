"""Centralized scheduler for all periodic tasks.

Add scheduled jobs here instead of creating separate asyncio tasks in bot.py.
"""
import asyncio
import logging

logger = logging.getLogger(__name__)

_scheduled_tasks: list[dict] = []


def every(seconds: int, description: str = ""):
    """Decorator to register a periodic task."""
    def decorator(func):
        _scheduled_tasks.append({"func": func, "interval": seconds, "description": description})
        return func
    return decorator


async def run_scheduler():
    """Start all registered scheduled tasks."""
    if not _scheduled_tasks:
        logger.info("Scheduler: no tasks registered.")
        return

    logger.info(f"Scheduler: starting {len(_scheduled_tasks)} task(s)...")
    async def _wrapper(task_def):
        fn = task_def["func"]
        interval = task_def["interval"]
        desc = task_def["description"] or fn.__name__
        while True:
            try:
                await fn()
            except Exception as e:
                logger.error(f"Scheduler [{desc}]: {e}")
            await asyncio.sleep(interval)

    for t in _scheduled_tasks:
        asyncio.create_task(_wrapper(t))
