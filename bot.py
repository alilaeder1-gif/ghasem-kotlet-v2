import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message
from config import BOT_TOKEN, DATABASE_PATH, REDIS_ENABLED
from database import db
from cache import cache
from handlers import admin, welcome, rules, spam, ai_chat, misc, custom, persona, group_tracker, force_sub
from middlewares.anti_flood import AntiFloodMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN تنظیم نشده!")
        return

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    await db.connect()
    logger.info("پایگاه داده متصل شد.")

    await cache.connect()
    if cache.enabled:
        logger.info("Redis متصل شد.")
    else:
        logger.info("Redis فعال نیست (کش غیرفعال)")

    @dp.message()
    async def test_handler(message: Message):
        print(f"=== TEST HANDLER FIRED: text={message.text} ===", flush=True)
        if message.text and not message.text.startswith("/"):
            await message.reply(f"echo: {message.text}")

    dp.message.middleware(AntiFloodMiddleware())

    dp.include_router(admin.router)
    dp.include_router(welcome.router)
    dp.include_router(rules.router)
    dp.include_router(spam.router)
    dp.include_router(custom.router)
    dp.include_router(persona.router)
    dp.include_router(group_tracker.router)
    dp.include_router(force_sub.router)
    dp.include_router(ai_chat.router)
    dp.include_router(misc.router)

    logger.info("ربات شروع به کار کرد!")
    try:
        await dp.start_polling(bot)
    finally:
        await db.close()
        await cache.close()
        await bot.session.close()
        logger.info("ربات متوقف شد.")


if __name__ == "__main__":
    asyncio.run(main())
