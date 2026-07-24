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
from config import BOT_TOKEN, DATABASE_PATH, REDIS_ENABLED, GROQ_API_KEY, GROQ_KEYS
from database import db
from cache import cache
from handlers import admin, welcome, rules, spam, misc, custom, persona, group_tracker, force_sub, fun, admin_bot, persian_cmds, settings_panel
from middlewares.anti_flood import AntiFloodMiddleware
from handlers.ai_chat import ask_ai, extract_memory, split_sentences, detect_emotion
from handlers.personality_core import build_persona_prompt
from handlers.fun import reminder_worker
from handlers import user_relationships as rel_mod
from handlers import analytics as analytics_mod
from handlers import character_evolution as evol_mod
from handlers import group_modes as gm_mod
from handlers import quality_gate as qg_mod
from handlers import persona_signature as sig_mod
from handlers import router as router_mod
from handlers import response_quality as rq_mod
from handlers.ai_chat import _call_google, _call_deepseek, _get_openrouter, OPENROUTER_MODELS


async def _build_ai_prompt(settings: dict, persona_prompt: str = None, chat_id: int = None, emotion: str = None, context: dict = None) -> str:
    sliders = {}
    if chat_id:
        try:
            sliders = await db.get_personality_sliders(chat_id)
        except:
            pass
    settings_with_sliders = {**settings, **sliders}
    base = build_persona_prompt(settings_with_sliders, context=context)
    if persona_prompt:
        base += f"\n\n## شخصیت سفارشی\n{persona_prompt}"
    if emotion and emotion != "normal":
        base = base.replace("[پیش‌فرض]", "", 1)
        mood_label = {"friendly": "رفیق‌بازی", "annoyed": "عصبی", "serious": "جدی", "comedy": "طنز"}.get(emotion, "")
        if mood_label:
            base += f"\n\n## وضعیت فعلی: {mood_label}\nالان در حالت {mood_label} هستی. طبق این حالت رفتار کن."
    return base


async def ask_with_routing(user_msg: str, system_prompt: str, history: list, user_memory: str, qa_context: list, route_decision: router_mod.RouteDecision) -> str:
    failover_chain = router_mod.get_failover_chain(route_decision)
    last_error = None
    for provider, model in failover_chain:
        try:
            if provider == "gemini":
                response = await asyncio.to_thread(_call_google, user_msg, system_prompt, history)
            elif provider == "groq":
                from handlers.ai_chat import _get_groq
                client = _get_groq()
                if not client:
                    continue
                messages = [{"role": "system", "content": system_prompt}]
                if history:
                    for msg in history[-6:]:
                        role = "user" if msg.get("role") == "user" else "assistant"
                        messages.append({"role": role, "content": msg.get("content", "")})
                messages.append({"role": "user", "content": user_msg})
                from handlers.ai_chat import _call_groq
                response = _call_groq(client, model, messages)
            elif provider == "openrouter":
                client = _get_openrouter()
                if not client:
                    continue
                messages = [{"role": "system", "content": system_prompt}]
                if history:
                    for msg in history[-6:]:
                        role = "user" if msg.get("role") == "user" else "assistant"
                        messages.append({"role": role, "content": msg.get("content", "")})
                messages.append({"role": "user", "content": user_msg})
                from handlers.ai_chat import _call_groq
                response = _call_groq(client, model, messages)
            else:
                continue
            if not response or response.startswith(("⚠", "⏳")):
                last_error = response
                continue
            if rq_mod.needs_failover(response, user_msg, ""):
                continue
            return response
        except Exception as e:
            last_error = str(e)
            continue
    return last_error or "⚠️ همه مدل‌ها محدودیت دارن. بعداً امتحان کن."


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

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
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
    dp.include_router(admin_bot.router)
    dp.include_router(persian_cmds.router)
    dp.include_router(misc.router)
    dp.include_router(welcome.router)
    dp.include_router(rules.router)
    dp.include_router(spam.router)
    dp.include_router(custom.router)
    dp.include_router(persona.router)
    dp.include_router(group_tracker.router)
    dp.include_router(force_sub.router)
    dp.include_router(fun.router)
    dp.include_router(settings_panel.router)

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

        if message.chat.type in ("group", "supergroup"):
            settings = await db.get_group_settings(message.chat.id)
            if settings and settings.get("force_sub_enabled"):
                channel = settings.get("force_sub_channel", "")
                if channel and not await force_sub.is_subscribed(message.bot, message.from_user.id, channel):
                    return

        if message.chat.type in ("group", "supergroup"):
            replies = await db.get_auto_replies(message.chat.id)
            for r in replies:
                keyword = r["keyword"].lower()
                if r.get("is_regex", False):
                    try:
                        if re.search(keyword, user_msg.lower()):
                            await message.reply(r["response"])
                            return
                    except:
                        pass
                else:
                    if keyword in user_msg.lower():
                        await message.reply(r["response"])
                        return

        settings = await db.get_group_settings(message.chat.id)
        emotion = detect_emotion(user_msg)

        # Group mode adjustment
        group_mode = {}
        humor_adjust = 0
        energy_adjust = 0
        try:
            group_mode = await gm_mod.get_group_mode(message.chat.id)
            mode_sliders = gm_mod.adjust_sliders_for_mode(
                {"humor_level": settings.get("humor_level", 6), "energy": settings.get("energy", 8)},
                group_mode,
            )
            humor_adjust = mode_sliders.get("humor_level", 6)
            energy_adjust = mode_sliders.get("energy", 8)
        except:
            pass

        # User relationship tracking
        try:
            rel = await rel_mod.get_relationship(message.from_user.id, message.chat.id)
            style = await rel_mod.detect_speaking_style(user_msg)
            hp = await rel_mod.detect_humor_preference(user_msg)
            mood = await rel_mod.detect_mood(user_msg)
            await rel_mod.update_relationship(
                message.from_user.id, message.chat.id,
                speaking_style=style, humor_preference=hp, interaction_mood=mood,
            )
            await rel_mod.track_interaction(message.from_user.id, message.chat.id, user_msg[:100])
        except:
            pass

        is_group = message.chat.type in ("group", "supergroup")
        route_decision = router_mod.route(user_msg, is_group=is_group)
        topics = router_mod.detect_topic(user_msg)
        prompt_context = {
            "is_group": is_group,
            "topic": " ".join(topics),
            "intent": route_decision.intent,
        }
        system_prompt = await _build_ai_prompt(settings, persona["prompt"] if persona else None, message.chat.id, emotion, context=prompt_context)
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

        try:
            history = await db.get_chat_history(message.chat.id, limit=3)
        except:
            history = []

        user_memory = ""
        try:
            user_memory = await db.get_user_memory(message.from_user.id, message.chat.id)
        except:
            pass

        qa_context = await db.search_similar_qa(message.chat.id, user_msg)

        sentences = split_sentences(user_msg)
        if len(sentences) > 1:
            responses = []
            for s in sentences[:3]:
                resp = await ask_with_routing(s, system_prompt, history, user_memory, qa_context, route_decision)
                if not resp.startswith("⚠") and not resp.startswith("⏳"):
                    responses.append(resp)
                await asyncio.sleep(0.5)
            response = "\n".join(responses[:3])
        else:
            response = await ask_with_routing(user_msg, system_prompt, history, user_memory, qa_context, route_decision)

        if not response or response.startswith("⚠") or response.startswith("⏳"):
            return

        # Response Quality Check (failover if bad)
        if rq_mod.needs_failover(response, user_msg, emotion):
            response = await ask_with_routing(user_msg, system_prompt, history, user_memory, qa_context, route_decision)
            if not response or response.startswith(("⚠", "⏳")):
                return

        # Quality Gate
        humor_used = emotion not in ("annoyed", "sad", "angry")
        qg_result = await qg_mod.evaluate_response(user_msg, response, emotion)
        if not qg_result["passed"]:
            if qg_result.get("length_ok") is False:
                response = response[:67] + "..."
            if qg_result.get("personality_ok") is False:
                response = "داداش " + response.lower()
            if qg_result.get("humor_ok") is False and humor_used:
                response = response.replace("😂", "").replace("😄", "").replace("😎", "").strip()

        # Persona Signature
        response = sig_mod.apply_signature(response)

        if len(response) > 70:
            response = response[:67] + "..."

        try:
            await message.reply(response)
            await db.save_chat(message.chat.id, message.from_user.id, user_msg, response)
            try:
                new_memory = await extract_memory(user_msg, response, user_memory)
                if new_memory and new_memory != user_memory:
                    await db.save_user_memory(message.from_user.id, message.chat.id, new_memory)
            except:
                pass
        except:
            pass

        # Post-response analytics
        try:
            await analytics_mod.log_conversation(
                message.chat.id, message.from_user.id, user_msg, response,
                emotion=emotion, humor_used=humor_used,
                quality_score=qg_result.get("score", 1.0),
                passed_gate=qg_result["passed"],
            )
        except:
            pass

        # Character evolution — track used phrases
        try:
            for word in ["داداش", "والا", "دمت", "بابا"]:
                if word in response:
                    await evol_mod.record_usage(word, "slang", success=True)
        except:
            pass

        try:
            await db.save_qa_pair(message.chat.id, message.from_user.id, user_msg, response)
        except:
            pass

    @dp.message(F.voice)
    async def voice_handler(message: Message):
        try:
            await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
            import io
            import speech_recognition as sr
            import tempfile
            import os

            file = await message.bot.get_file(message.voice.file_id)
            file_bytes = await message.bot.download_file(file.file_path)
            if isinstance(file_bytes, io.BytesIO):
                file_bytes = file_bytes.getvalue()

            user_msg = ""
            recognizer = sr.Recognizer()

            # اول با Groq Whisper (با چرخش کلیدها)
            _groq_idx = 0
            for attempt in range(len(GROQ_KEYS)):
                api_key = GROQ_KEYS[_groq_idx % len(GROQ_KEYS)]
                _groq_idx += 1
                if not api_key:
                    continue
                try:
                    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
                        f.write(file_bytes)
                        tmp_path = f.name
                    with sr.AudioFile(tmp_path) as source:
                        audio = recognizer.record(source)
                    user_msg = recognizer.recognize_groq(audio, api_key=api_key)
                    os.unlink(tmp_path)
                    break
                except Exception as e:
                    logger.warning(f"Groq STT attempt {attempt+1} failed: {e}")
                    user_msg = ""
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass

            # fallback: Google رایگان
            if not user_msg:
                try:
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                        f.write(file_bytes)
                        tmp_path = f.name
                    with sr.AudioFile(tmp_path) as source:
                        audio = recognizer.record(source)
                    user_msg = recognizer.recognize_google(audio, language="fa-IR")
                    os.unlink(tmp_path)
                except Exception as e:
                    logger.warning(f"Google STT failed: {e}")
                    return await message.reply("⚠️ نتونستم ویست رو بفهمم.")

            if not user_msg:
                return await message.reply("⚠️ چیزی نگفتی توی ویس.")

            persona = await db.get_persona(message.chat.id)
            if persona and not persona["enabled"]:
                return
            settings = await db.get_group_settings(message.chat.id)
            emotion = detect_emotion(user_msg)
            system_prompt = await _build_ai_prompt(settings, persona["prompt"] if persona else None, message.chat.id, emotion)

            history = []
            try:
                history = await db.get_chat_history(message.chat.id, limit=2)
            except:
                pass

            qa_context = await db.search_similar_qa(message.chat.id, user_msg)
            response = await ask_ai(user_msg, system_prompt, history, qa_context=qa_context)
            if response.startswith("⚠") or response.startswith("⏳"):
                return
            else:
                if len(response) > 70:
                    response = response[:67] + "..."
                await message.reply(f"🎤 {response}")
                try:
                    await db.save_qa_pair(message.chat.id, message.from_user.id, user_msg, response)
                except:
                    pass
        except Exception as e:
            await message.reply(f"⚠️ خطا: {str(e)[:100]}")

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
