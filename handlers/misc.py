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

    s = await db.get_group_settings(message.chat.id)

    def build_kb(st):
        b = InlineKeyboardBuilder()
        ai = st.get("ai_chat_enabled", True)
        sp = st.get("spam_protection", True)
        fl = st.get("flood_protection", True)
        wl = st.get("welcome_enabled", True)
        ld = st.get("link_delete_enabled", False)
        fs = st.get("force_sub_enabled", False)
        b.button(text=f"{'🟢' if ai else '🔴'} هوش مصنوعی", callback_data=f"sett|ai|{message.chat.id}")
        b.button(text=f"{'🟢' if sp else '🔴'} محافظت اسپم", callback_data=f"sett|spam|{message.chat.id}")
        b.button(text=f"{'🟢' if fl else '🔴'} محافظت سیل", callback_data=f"sett|flood|{message.chat.id}")
        b.button(text=f"{'🟢' if wl else '🔴'} خوشامدگویی", callback_data=f"sett|welcome|{message.chat.id}")
        b.button(text=f"{'🟢' if ld else '🔴'} حذف خودکار لینک", callback_data=f"sett|linkdel|{message.chat.id}")
        b.button(text=f"{'🟢' if fs else '🔴'} عضویت اجباری", callback_data=f"sett|forcesub|{message.chat.id}")
        b.adjust(2)
        return b.as_markup()

    def status_text(st):
        return (
            f"⚙️ **پنل تنظیمات گروه**\n\n"
            f"🤖 **هوش مصنوعی:** {'✅ فعال' if st.get('ai_chat_enabled', True) else '❌ غیرفعال'}\n"
            f"   کتلت به سوالات هوشمند جواب میده\n\n"
            f"🛡 **محافظت اسپم:** {'✅ فعال' if st.get('spam_protection', True) else '❌ غیرفعال'}\n"
            f"   تشخیص و حذف پیام‌های اسپم\n\n"
            f"🌊 **محافظت سیل:** {'✅ فعال' if st.get('flood_protection', True) else '❌ غیرفعال'}\n"
            f"   جلوگیری از پیام‌های پشت سر هم\n\n"
            f"👋 **خوشامدگویی:** {'✅ فعال' if st.get('welcome_enabled', True) else '❌ غیرفعال'}\n"
            f"   پیام خوشامد به اعضای جدید\n\n"
            f"🔗 **حذف خودکار لینک:** {'✅ فعال' if st.get('link_delete_enabled', False) else '❌ غیرفعال'}\n"
            f"   حذف لینک‌های کاربران (قابل تنظیم با /linkdelete)\n\n"
            f"📢 **عضویت اجباری:** {'✅ فعال' if st.get('force_sub_enabled', False) else '❌ غیرفعال'}\n"
            f"   کاربران باید عضو کانال بشن\n\n"
            f"━━━━━━━━━━━━━━━\n"
            f"روی هر دکمه بزن تا وضعیت تغییر کنه 👇"
        )

    await message.reply(status_text(s), reply_markup=build_kb(s))


@router.callback_query(F.data.startswith("sett|"))
async def settings_cb(cq):
    from database import db
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    parts = cq.data.split("|")
    action = parts[1]
    chat_id = int(parts[2])

    try:
        chat_member = await cq.bot.get_chat_member(chat_id, cq.from_user.id)
        if chat_member.status not in ("creator", "administrator"):
            return await cq.answer("❌ فقط ادمین", show_alert=True)
    except:
        return await cq.answer("❌ خطا", show_alert=True)

    s = await db.get_group_settings(chat_id)

    toggles = {
        "ai": ("ai_chat_enabled", not s.get("ai_chat_enabled", True)),
        "spam": ("spam_protection", not s.get("spam_protection", True)),
        "flood": ("flood_protection", not s.get("flood_protection", True)),
        "welcome": ("welcome_enabled", not s.get("welcome_enabled", True)),
        "linkdel": ("link_delete_enabled", not s.get("link_delete_enabled", False)),
        "forcesub": ("force_sub_enabled", not s.get("force_sub_enabled", False)),
    }

    if action not in toggles:
        return await cq.answer("❌", show_alert=True)

    key, val = toggles[action]
    await db.set_group_settings(chat_id, **{key: int(val)})
    await cq.answer(f"{'🟢 فعال' if val else '🔴 غیرفعال'} شد ✅", show_alert=False)

    s = await db.get_group_settings(chat_id)

    def build_kb(st):
        b = InlineKeyboardBuilder()
        b.button(text=f"{'🟢' if st.get('ai_chat_enabled', True) else '🔴'} هوش مصنوعی", callback_data=f"sett|ai|{chat_id}")
        b.button(text=f"{'🟢' if st.get('spam_protection', True) else '🔴'} محافظت اسپم", callback_data=f"sett|spam|{chat_id}")
        b.button(text=f"{'🟢' if st.get('flood_protection', True) else '🔴'} محافظت سیل", callback_data=f"sett|flood|{chat_id}")
        b.button(text=f"{'🟢' if st.get('welcome_enabled', True) else '🔴'} خوشامدگویی", callback_data=f"sett|welcome|{chat_id}")
        b.button(text=f"{'🟢' if st.get('link_delete_enabled', False) else '🔴'} حذف خودکار لینک", callback_data=f"sett|linkdel|{chat_id}")
        b.button(text=f"{'🟢' if st.get('force_sub_enabled', False) else '🔴'} عضویت اجباری", callback_data=f"sett|forcesub|{chat_id}")
        b.adjust(2)
        return b.as_markup()

    def status_text(st):
        return (
            f"⚙️ **پنل تنظیمات گروه**\n\n"
            f"🤖 **هوش مصنوعی:** {'✅ فعال' if st.get('ai_chat_enabled', True) else '❌ غیرفعال'}\n"
            f"   کتلت به سوالات هوشمند جواب میده\n\n"
            f"🛡 **محافظت اسپم:** {'✅ فعال' if st.get('spam_protection', True) else '❌ غیرفعال'}\n"
            f"   تشخیص و حذف پیام‌های اسپم\n\n"
            f"🌊 **محافظت سیل:** {'✅ فعال' if st.get('flood_protection', True) else '❌ غیرفعال'}\n"
            f"   جلوگیری از پیام‌های پشت سر هم\n\n"
            f"👋 **خوشامدگویی:** {'✅ فعال' if st.get('welcome_enabled', True) else '❌ غیرفعال'}\n"
            f"   پیام خوشامد به اعضای جدید\n\n"
            f"🔗 **حذف خودکار لینک:** {'✅ فعال' if st.get('link_delete_enabled', False) else '❌ غیرفعال'}\n"
            f"   حذف لینک‌های کاربران (قابل تنظیم با /linkdelete)\n\n"
            f"📢 **عضویت اجباری:** {'✅ فعال' if st.get('force_sub_enabled', False) else '❌ غیرفعال'}\n"
            f"   کاربران باید عضو کانال بشن\n\n"
            f"━━━━━━━━━━━━━━━\n"
            f"روی هر دکمه بزن تا وضعیت تغییر کنه 👇"
        )

    await cq.message.edit_text(status_text(s), reply_markup=build_kb(s))
