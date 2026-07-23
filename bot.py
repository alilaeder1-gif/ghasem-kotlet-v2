import asyncio
import logging
import re
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message
from aiogram import F
from config import BOT_TOKEN, DATABASE_PATH, REDIS_ENABLED
from database import db
from cache import cache
from handlers import admin, welcome, rules, spam, misc, custom, persona, group_tracker, force_sub, fun
from middlewares.anti_flood import AntiFloodMiddleware
from handlers.ai_chat import ask_ai, DEFAULT_PROMPT
from handlers.fun import reminder_worker


GREETING_PATTERNS = [
    re.compile(r'س+ل+ا+م+'),        # سسسلالالالاممم
    re.compile(r'چ+ط+و+ر+[یي]+'),   # چطوووورییی
    re.compile(r'چ+ط+و+ر+ی+ن+'),    # چطورین
    re.compile(r'چ+خ+ب+ر+'),        # چخبر
    re.compile(r'د+ر+و+د+'),        # درود
    re.compile(r'ع+ل+ی+ک+'),        # علیک
    re.compile(r'خ+و+ب+[یي]+'),     # خوبی
    re.compile(r'خ+و+ب+ی+ن+'),      # خوبین
    re.compile(r'ح+ا+ل+ت+چ+ط+و+ر+'),# حالت چطور
    re.compile(r'ح+ا+ل+ت+ش+و+م+ا+'),# حالت شما
    re.compile(r'چ+ط+و+ر+[هه]+'),   # چطوره
    re.compile(r'چ+ی+ز+ی+'),        # چیزی
    re.compile(r'ک+ج+ا+[یي]+'),     # کجایی
    re.compile(r'چ+ن+د+م+ی+ن+'),    # چندمین
    re.compile(r'م+ا+ل+ی+'),        # مالی
    re.compile(r'ت+و+[یي]+'),       # تویی
    re.compile(r'ی+ه+ر+و+چ+ی+'),    # یهروچی
    re.compile(r'ج+و+ن+م+'),        # جونم
    re.compile(r'چ+ی+ز+ی+'),        # چیزی
]


def is_persian_greeting(text):
    clean = re.sub(r'[\s\.\,\?\=\!\-]', '', text)
    for p in GREETING_PATTERNS:
        if p.search(clean):
            return True
    return False

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

    bio = "سلام جوون! کُتلتم، رفیق باحال گروه. هر کی حوصله‌ش سر رفت من اینجام 😎"
    try:
        await bot.set_my_description(bio)
        await bot.set_my_short_description("کُتلت | رفیق باحال گروه")
    except:
        pass

    dp.message.middleware(AntiFloodMiddleware())

    dp.include_router(admin.router)
    dp.include_router(welcome.router)
    dp.include_router(rules.router)
    dp.include_router(spam.router)
    dp.include_router(custom.router)
    dp.include_router(persona.router)
    dp.include_router(group_tracker.router)
    dp.include_router(force_sub.router)
    dp.include_router(fun.router)

    asyncio.create_task(reminder_worker())

    @dp.message(F.text)
    async def ai_chat_handler(message: Message):
        print(f"=== AI_CHAT FROM BOT.PY ===", flush=True)
        user_msg = message.text.strip()
        if user_msg.startswith("/"):
            return

        if message.chat.type in ("group", "supergroup"):
            try:
                await db.add_group(message.chat.id, message.chat.title or "بدون نام", message.chat.username or "")
                member_count = await message.bot.get_chat_member_count(message.chat.id)
                await db.update_group_member_count(message.chat.id, member_count)
            except:
                pass
            bot_info = await message.bot.get_me()
            is_mention = f"@{bot_info.username}" in user_msg
            is_reply = (
                message.reply_to_message
                and message.reply_to_message.from_user
                and message.reply_to_message.from_user.id == bot_info.id
            )
            user_msg_lower = user_msg.lower()
            is_name_called = any(k in user_msg_lower for k in ["کتلت", "کتی", "kotlet", "قاسم"])
            is_greeting = is_persian_greeting(user_msg_lower)
            if is_greeting and message.reply_to_message:
                is_reply_to_bot = (
                    message.reply_to_message.from_user
                    and message.reply_to_message.from_user.id == bot_info.id
                )
                if not is_reply_to_bot:
                    is_greeting = False
            if not is_mention and not is_reply and not is_name_called and not is_greeting:
                return
            if is_mention:
                user_msg = user_msg.replace(f"@{bot_info.username}", "").strip()
            elif is_reply:
                pass

        if not user_msg:
            user_msg = "سلام"

        persona = await db.get_persona(message.chat.id)
        if persona and not persona["enabled"]:
            return

        system_prompt = persona["prompt"] if persona else DEFAULT_PROMPT
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
        response = await ask_ai(user_msg, system_prompt)

        if response.startswith("⚠") or response.startswith("⏳"):
            await message.reply(response)
            return

        try:
            await message.reply(response)
        except:
            pass

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
