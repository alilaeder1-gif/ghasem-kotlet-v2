from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from database import db
from handlers.ai_chat import ask_code

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    try:
        if message.chat.type in ("group", "supergroup"):
            return await message.reply(
                "سلام جوون! قاسم کتلتم، کتلت آماده! هر فرمانی دارین بفرمایین 😎\n\n"
                "🤖 **کُتلت** - ربات هوشمند مدیریت گروه\n\n"
                "⚙️ **دستورات ضروری:**\n"
                "/settings - پنل تنظیمات گروه\n"
                "/rules - قوانین گروه\n"
                "/stats - آمار گروه\n"
                "/id - آیدی شما\n"
                "/draw - نقاشی با هوش مصنوعی\n"
                "/code - کدنویسی با AI\n\n"
                "🎮 **سرگرمی:**\n"
                "/game - بازی حدس کلمه\n"
                "/remind - تنظیم یادآوری\n\n"
                "🔐 **مدیریت (ادمین):**\n"
                "/ban, /kick, /mute, /pin, /tag\n"
                "/setrules, /setwelcome, /linkdelete\n"
                "/setprompt, /toggleai, /forcesub\n"
                "/setcmd, /setreply\n\n"
                "🤖 **چت هوشمند:**\n"
                "@کتلت + پیام - حرف زدن با هوش مصنوعی"
            )

        await message.reply(
            "سلام جوون! قاسم کتلتم، کتلت آماده! هر فرمانی دارین بفرمایین 😎\n\n"
            "🤖 **کُتلت** - ربات هوشمند مدیریت گروه\n\n"
            "⚙️ **دستورات:**\n"
            "/settings - پنل تنظیمات\n"
            "/stats - آمار\n"
            "/id - آیدی شما\n"
            "/draw - نقاشی با AI\n"
            "/code - کدنویسی\n"
            "/game - بازی\n"
            "/remind - یادآوری\n\n"
            "🔐 **ادمین:**\n"
            "/ban, /kick, /mute, /tag\n"
            "/setrules, /setwelcome, /linkdelete\n"
            "/forcesub, /setprompt, /toggleai\n"
            "/setcmd, /setreply\n\n"
            "🤖 **چت هوشمند:**\n"
            "@کتلت + پیام"
        )
    except Exception as e:
        try:
            await message.reply("سلام جوون! کتلت آماده است 😎\n/settings - تنظیمات\n/stats - آمار\n/id - آیدی شما")
        except:
            pass


@router.message(Command("help"))
async def cmd_help(message: Message):
    await cmd_start(message)


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    try:
        if message.chat.type in ("group", "supergroup"):
            member_count = await message.bot.get_chat_member_count(message.chat.id)
            await message.reply(
                f"📊 آمار گروه:\n\n"
                f"👥 تعداد اعضا: {member_count}\n"
                f"📛 نام گروه: {message.chat.title}"
            )
        else:
            await message.reply("📊 این دستور فقط در گروه قابل استفاده است.")
    except Exception as e:
        await message.reply(f"خطا در دریافت آمار: {e}")


@router.message(Command("id"))
async def cmd_id(message: Message):
    await message.reply(f"🆔 آیدی عددی شما:\n`{message.from_user.id}`")


@router.message(Command("draw"))
async def cmd_draw(message: Message):
    prompt = message.text.replace("/draw", "").replace("/draw@kotletaiBot", "").strip()
    if not prompt:
        return await message.reply("مثال: /draw گربه فضایی")
    url = f"https://image.pollinations.ai/prompt/{prompt}?width=1024&height=1024&nologo=true"
    try:
        await message.reply_photo(photo=url, caption=f"🎨 {prompt}")
    except:
        await message.reply(url)


@router.message(Command("code"))
async def cmd_code(message: Message):
    prompt = message.text.replace("/code", "").replace("/code@kotletaiBot", "").strip()
    if not prompt:
        return await message.reply("مثال: /code یک فانکشن فیبوناچی به پایتون بنویس")
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    response = await ask_code(prompt)
    await message.reply(response[:4000])


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        return await message.reply("❌ این دستور فقط در گروه قابل استفاده است.")
    chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status not in ("creator", "administrator"):
        return await message.reply("❌ فقط ادمین‌ها دسترسی دارن.")

    from handlers.settings_panel import show_main
    await show_main(message, message.chat.id, edit=False)


@router.message(Command("prompt"))
async def cmd_prompt(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        return await message.reply("❌ این دستور فقط در گروه قابل استفاده است.")
    chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status not in ("creator", "administrator"):
        return await message.reply("❌ فقط ادمین")
    from bot import _build_ai_prompt
    from handlers.ai_chat import detect_emotion
    settings = await db.get_group_settings(message.chat.id)
    text = message.text.replace("/prompt", "").strip() or "تست"
    emo = detect_emotion(text)
    prompt = await _build_ai_prompt(settings, chat_id=message.chat.id, emotion=emo)
    preview = prompt[:3500]
    await message.reply(f"🧠 **Debug Prompt**\nاحساس: {emo}\n\n`{preview}`")
