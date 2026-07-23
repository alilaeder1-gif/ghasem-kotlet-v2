import asyncio
import logging
import os
import re
import tempfile
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


def is_persian_greeting(text):
    clean = re.sub(r'[\s\.\,\?\=\!\-]', '', text)
    patterns = [
        r'س+ل+ا*م*', r'س+ل+م+',
        r'چ+ط+و+ر+',
        r'د+ر+و+د+',
        r'ع+ل+ی+ک+',
        r'خ+و+ب+[یي]',
        r'چ+خ+ب+ر+',
    ]
    return any(re.search(p, clean) for p in patterns)

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

    @dp.message(F.text, ~F.text.startswith("/"))
    async def ai_chat_handler(message: Message):
        print(f"=== AI_CHAT FROM BOT.PY ===", flush=True)
        user_msg = message.text.strip()

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

        try:
            history = await db.get_chat_history(message.chat.id, limit=6)
        except:
            history = []

        response = await ask_ai(user_msg, system_prompt, history)

        if response.startswith("⚠") or response.startswith("⏳"):
            await message.reply(response)
            return

        try:
            await message.reply(response)
            await db.save_chat(message.chat.id, message.from_user.id, user_msg, response)
        except:
            pass

    @dp.message(F.voice)
    async def voice_handler(message: Message):
        try:
            await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
            import io
            import httpx

            file = await message.bot.get_file(message.voice.file_id)
            file_bytes = await message.bot.download_file(file.file_path)
            if isinstance(file_bytes, io.BytesIO):
                file_bytes = file_bytes.getvalue()

            api_key = os.getenv("GROQ_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
            if not api_key:
                return await message.reply("⚠️ خطا: API key تنظیم نشده.")

            resp = httpx.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": ("voice.ogg", file_bytes, "audio/ogg")},
                data={"model": "whisper-large-v3", "language": "fa"},
                timeout=30
            )
            if resp.status_code != 200:
                return await message.reply(f"⚠️ نتونستم ویست رو بفهمم. ({resp.status_code})")
            user_msg = resp.json().get("text", "").strip()
            if not user_msg:
                return await message.reply("⚠️ چیزی نگفتی توی ویس.")

            user_msg_lower = user_msg.lower()
            is_name = any(k in user_msg_lower for k in ["کتلت", "کتی", "kotlet", "قاسم"])
            is_greet = is_persian_greeting(user_msg_lower)
            if message.chat.type in ("group", "supergroup") and not is_name and not is_greet:
                return

            persona = await db.get_persona(message.chat.id)
            if persona and not persona["enabled"]:
                return
            system_prompt = persona["prompt"] if persona else DEFAULT_PROMPT
            response = await ask_ai(user_msg, system_prompt)
            if response.startswith("⚠") or response.startswith("⏳"):
                await message.reply(response)
            else:
                await message.reply(f"🎤 {response}")
        except Exception as e:
            await message.reply(f"⚠️ خطا: {str(e)[:100]}")

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
