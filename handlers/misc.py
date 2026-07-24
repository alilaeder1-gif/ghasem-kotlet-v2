from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from database import db
from config import ADMIN_IDS
from handlers.ai_chat import ask_code

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
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

    await message.answer(
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


@router.message(Command("help"))
async def cmd_help(message: Message):
    await cmd_start(message)


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    try:
        member_count = await message.bot.get_chat_member_count(message.chat.id)
        await message.reply(
            f"📊 آمار گروه:\n\n"
            f"👥 تعداد اعضا: {member_count}\n"
            f"📛 نام گروه: {message.chat.title}"
        )
    except Exception as e:
        await message.reply(f"خطا در دریافت آمار: {e}")


@router.message(Command("id"))
async def cmd_id(message: Message):
    await message.reply(f"🆔 آیدی عددی شما:\n<code>{message.from_user.id}</code>")


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
        return
    chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status not in ("creator", "administrator"):
        return await message.reply("❌ فقط ادمین‌ها دسترسی دارن.")

    from database import db
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    settings = await db.get_group_settings(message.chat.id)

    def build_kb(s):
        b = InlineKeyboardBuilder()
        ai = s.get("ai_chat_enabled", True)
        sp = s.get("spam_protection", True)
        fl = s.get("flood_protection", True)
        wl = s.get("welcome_enabled", True)
        ld = s.get("link_delete_enabled", False)
        fs = s.get("force_sub_enabled", False)
        b.button(text=f"{'✅' if ai else '❌'} هوش", callback_data=f"sett_ai_{message.chat.id}")
        b.button(text=f"{'✅' if sp else '❌'} اسپم", callback_data=f"sett_spam_{message.chat.id}")
        b.button(text=f"{'✅' if fl else '❌'} سیل", callback_data=f"sett_flood_{message.chat.id}")
        b.button(text=f"{'✅' if wl else '❌'} خوشامد", callback_data=f"sett_welcome_{message.chat.id}")
        b.button(text=f"{'✅' if ld else '❌'} لینک", callback_data=f"sett_linkdel_{message.chat.id}")
        b.button(text=f"{'✅' if fs else '❌'} اجباری", callback_data=f"sett_forcesub_{message.chat.id}")
        b.adjust(2)
        return b.as_markup()

    await message.reply("⚙️ **تنظیمات گروه**\nروی دکمه بزن تا تغییر کنه.", reply_markup=build_kb(settings))


@router.callback_query(F.data.startswith("sett_"))
async def settings_cb(cq):
    from database import db
    chat_id = int(cq.data.split("_")[-1])
    action = cq.data.rsplit("_", 2)[1]

    try:
        chat_member = await cq.bot.get_chat_member(chat_id, cq.from_user.id)
        if chat_member.status not in ("creator", "administrator"):
            return await cq.answer("❌ فقط ادمین", show_alert=True)
    except:
        return await cq.answer("❌ خطا", show_alert=True)

    s = await db.get_group_settings(chat_id)
    if not s:
        return

    toggles = {
        "ai": ("ai_chat_enabled", not s.get("ai_chat_enabled", True)),
        "spam": ("spam_protection", not s.get("spam_protection", True)),
        "flood": ("flood_protection", not s.get("flood_protection", True)),
        "welcome": ("welcome_enabled", not s.get("welcome_enabled", True)),
        "linkdel": ("link_delete_enabled", not s.get("link_delete_enabled", False)),
        "forcesub": ("force_sub_enabled", not s.get("force_sub_enabled", False)),
    }

    if action in toggles:
        key, val = toggles[action]
        await db.set_group_settings(chat_id, **{key: int(val)})
        await cq.answer(f"{'✅ فعال' if val else '❌ غیرفعال'} شد.", show_alert=False)

        s = await db.get_group_settings(chat_id)
        def build_kb(s):
            b = InlineKeyboardBuilder()
            b.button(text=f"{'✅' if s.get('ai_chat_enabled', True) else '❌'} هوش", callback_data=f"sett_ai_{chat_id}")
            b.button(text=f"{'✅' if s.get('spam_protection', True) else '❌'} اسپم", callback_data=f"sett_spam_{chat_id}")
            b.button(text=f"{'✅' if s.get('flood_protection', True) else '❌'} سیل", callback_data=f"sett_flood_{chat_id}")
            b.button(text=f"{'✅' if s.get('welcome_enabled', True) else '❌'} خوشامد", callback_data=f"sett_welcome_{chat_id}")
            b.button(text=f"{'✅' if s.get('link_delete_enabled', False) else '❌'} لینک", callback_data=f"sett_linkdel_{chat_id}")
            b.button(text=f"{'✅' if s.get('force_sub_enabled', False) else '❌'} اجباری", callback_data=f"sett_forcesub_{chat_id}")
            b.adjust(2)
            return b.as_markup()
        await cq.message.edit_reply_markup(reply_markup=build_kb(s))
