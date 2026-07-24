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
    await show_main_panel(message, s, edit=False)


def _main_kb(st, chat_id):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    b.button(text=f"{'🟢' if st.get('ai_chat_enabled', True) else '🔴'} هوش مصنوعی", callback_data=f"sett|ai|{chat_id}")
    b.button(text=f"{'🟢' if st.get('spam_protection', True) else '🔴'} محافظت اسپم", callback_data=f"sett|spam|{chat_id}")
    b.button(text=f"{'🟢' if st.get('flood_protection', True) else '🔴'} محافظت سیل", callback_data=f"sett|flood|{chat_id}")
    b.button(text=f"{'🟢' if st.get('welcome_enabled', True) else '🔴'} خوشامدگویی", callback_data=f"sett|welcome|{chat_id}")
    b.button(text=f"{'🟢' if st.get('link_delete_enabled', False) else '🔴'} حذف خودکار لینک", callback_data=f"sett|linkdel|{chat_id}")
    b.button(text=f"{'🟢' if st.get('force_sub_enabled', False) else '🔴'} عضویت اجباری", callback_data=f"sett|forcesub|{chat_id}")
    b.button(text="🧠 تنظیمات هوش مصنوعی", callback_data=f"sett|ai_panel|{chat_id}")
    b.adjust(2)
    return b.as_markup()


def _main_text(st):
    return (
        f"⚙️ **پنل تنظیمات گروه**\n\n"
        f"🤖 **هوش مصنوعی:** {'✅ فعال' if st.get('ai_chat_enabled', True) else '❌ غیرفعال'}\n"
        f"🛡 **محافظت اسپم:** {'✅ فعال' if st.get('spam_protection', True) else '❌ غیرفعال'}\n"
        f"🌊 **محافظت سیل:** {'✅ فعال' if st.get('flood_protection', True) else '❌ غیرفعال'}\n"
        f"👋 **خوشامدگویی:** {'✅ فعال' if st.get('welcome_enabled', True) else '❌ غیرفعال'}\n"
        f"🔗 **حذف خودکار لینک:** {'✅ فعال' if st.get('link_delete_enabled', False) else '❌ غیرفعال'}\n"
        f"📢 **عضویت اجباری:** {'✅ فعال' if st.get('force_sub_enabled', False) else '❌ غیرفعال'}\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"روی هر دکمه بزن تا وضعیت تغییر کنه 👇"
    )


_AI_BEHAVIORS = ["default", "friendly", "formal", "funny", "cool", "polite"]
_AI_BEHAVIOR_NAMES = {
    "default": "پیش‌فرض", "friendly": "دوستانه", "formal": "رسمی",
    "funny": "شوخ", "cool": "باحال", "polite": "مودب"
}
_AI_TONES = ["tehrani", "turkish", "kurdish", "gilaki", "normal"]
_AI_TONE_NAMES = {
    "tehrani": "تهرونی", "turkish": "ترکی", "kurdish": "کردی",
    "gilaki": "گیلکی", "normal": "معمولی"
}


def _ai_panel_kb(st, chat_id):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    beh = st.get("ai_behavior", "default")
    tone = st.get("ai_tone", "tehrani")
    pers = st.get("ai_personality", 3)

    b.button(text=f"🧠 رفتار: {_AI_BEHAVIOR_NAMES.get(beh, beh)}", callback_data=f"sett|ai_beh|{chat_id}")
    b.button(text=f"🎙 لحن: {_AI_TONE_NAMES.get(tone, tone)}", callback_data=f"sett|ai_tone|{chat_id}")
    b.button(text=f"💪 شخصیت: {'⭐' * pers}{'☆' * (5-pers)}", callback_data=f"sett|ai_per|{chat_id}")
    b.button(text="🔙 برگشت", callback_data=f"sett|main|{chat_id}")
    b.adjust(2)
    return b.as_markup()


def _ai_panel_text(st):
    beh = st.get("ai_behavior", "default")
    tone = st.get("ai_tone", "tehrani")
    pers = st.get("ai_personality", 3)
    return (
        f"🧠 **تنظیمات هوش مصنوعی**\n\n"
        f"🎭 **حالت رفتار:** {_AI_BEHAVIOR_NAMES.get(beh, beh)}\n"
        f"   چطور با کاربرا حرف بزنه\n\n"
        f"🎙 **لحن گفتار:** {_AI_TONE_NAMES.get(tone, tone)}\n"
        f"   با چه لهجه‌ای حرف بزنه\n\n"
        f"💪 **درجه شخصیت:** {'⭐' * pers}{'☆' * (5-pers)} ({pers}/5)\n"
        f"   چقدر شخصیت و فیلتر داشته باشه (۱=ساکت, ۵=پررو)\n\n"
        f"برای تغییر روی هر دکمه بزن 👇"
    )


def _beh_kb(chat_id):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    for key in _AI_BEHAVIORS:
        b.button(text=_AI_BEHAVIOR_NAMES[key], callback_data=f"sett|set_beh|{key}|{chat_id}")
    b.button(text="🔙 برگشت", callback_data=f"sett|ai_panel|{chat_id}")
    b.adjust(2)
    return b.as_markup()


def _tone_kb(chat_id):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    for key in _AI_TONES:
        b.button(text=_AI_TONE_NAMES[key], callback_data=f"sett|set_tone|{key}|{chat_id}")
    b.button(text="🔙 برگشت", callback_data=f"sett|ai_panel|{chat_id}")
    b.adjust(2)
    return b.as_markup()


def _pers_kb(chat_id, current=3):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    for i in range(1, 6):
        sel = "✅" if i == current else f"{'⭐' * i}{'☆' * (5-i)}"
        b.button(text=f"{sel} ({i}/5)", callback_data=f"sett|set_pers|{i}|{chat_id}")
    b.button(text="🔙 برگشت", callback_data=f"sett|ai_panel|{chat_id}")
    b.adjust(2)
    return b.as_markup()


async def show_main_panel(msg_or_cq, s, edit=True, chat_id=None):
    if edit:
        await msg_or_cq.message.edit_text(_main_text(s), reply_markup=_main_kb(s, chat_id or msg_or_cq.message.chat.id))
    else:
        await msg_or_cq.reply(_main_text(s), reply_markup=_main_kb(s, s.get("_chat_id", msg_or_cq.chat.id)))


@router.callback_query(F.data.startswith("sett|"))
async def settings_cb(cq):
    from database import db
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    parts = cq.data.split("|")
    action = parts[1]
    chat_id = int(parts[2]) if len(parts) > 2 and parts[2].lstrip("-").isdigit() else cq.message.chat.id

    try:
        chat_member = await cq.bot.get_chat_member(chat_id, cq.from_user.id)
        if chat_member.status not in ("creator", "administrator"):
            return await cq.answer("❌ فقط ادمین", show_alert=True)
    except:
        return await cq.answer("❌ خطا", show_alert=True)

    s = await db.get_group_settings(chat_id)

    # ─── Toggles (main panel) ───
    if action in ("ai", "spam", "flood", "welcome", "linkdel", "forcesub"):
        key_map = {
            "ai": "ai_chat_enabled", "spam": "spam_protection", "flood": "flood_protection",
            "welcome": "welcome_enabled", "linkdel": "link_delete_enabled", "forcesub": "force_sub_enabled"
        }
        defaults = {"link_delete_enabled": False, "force_sub_enabled": False}
        cur = s.get(key_map[action], defaults.get(key_map[action], True))
        await db.set_group_settings(chat_id, **{key_map[action]: int(not cur)})
        await cq.answer(f"{'🟢 فعال' if not cur else '🔴 غیرفعال'} شد ✅", show_alert=False)
        s = await db.get_group_settings(chat_id)
        await cq.message.edit_text(_main_text(s), reply_markup=_main_kb(s, chat_id))
        return

    # ─── AI Panel ───
    if action == "ai_panel":
        await cq.message.edit_text(_ai_panel_text(s), reply_markup=_ai_panel_kb(s, chat_id))
        return

    # ─── Behavior selection page ───
    if action == "ai_beh":
        await cq.message.edit_text(
            f"🎭 **انتخاب حالت رفتار**\n\n"
            f"حالت فعلی: {_AI_BEHAVIOR_NAMES.get(s.get('ai_behavior', 'default'), s.get('ai_behavior', 'default'))}\n"
            f"روی حالت مورد نظر بزن:",
            reply_markup=_beh_kb(chat_id)
        )
        return

    if action == "set_beh":
        value = parts[3]
        await db.set_group_settings(chat_id, ai_behavior=value)
        await cq.answer(f"✅ حالت رفتار: {_AI_BEHAVIOR_NAMES.get(value, value)}", show_alert=False)
        s = await db.get_group_settings(chat_id)
        await cq.message.edit_text(_ai_panel_text(s), reply_markup=_ai_panel_kb(s, chat_id))
        return

    # ─── Tone selection page ───
    if action == "ai_tone":
        await cq.message.edit_text(
            f"🎙 **انتخاب لحن گفتار**\n\n"
            f"لحن فعلی: {_AI_TONE_NAMES.get(s.get('ai_tone', 'tehrani'), s.get('ai_tone', 'tehrani'))}\n"
            f"روی لحن مورد نظر بزن:",
            reply_markup=_tone_kb(chat_id)
        )
        return

    if action == "set_tone":
        value = parts[3]
        await db.set_group_settings(chat_id, ai_tone=value)
        await cq.answer(f"✅ لحن: {_AI_TONE_NAMES.get(value, value)}", show_alert=False)
        s = await db.get_group_settings(chat_id)
        await cq.message.edit_text(_ai_panel_text(s), reply_markup=_ai_panel_kb(s, chat_id))
        return

    # ─── Personality level selection ───
    if action == "ai_per":
        current = s.get("ai_personality", 3)
        levels_desc = {1: "🤖 رباتی", 2: "😐 معمولی", 3: "😊 خودمونی", 4: "😂 باحال", 5: "🔥 پررو"}
        desc = "\n".join([f"{'⭐'*i}{'☆'*(5-i)} ({i}) - {levels_desc[i]}" for i in range(1, 6)])
        await cq.message.edit_text(
            f"💪 **درجه شخصیت**\n\n"
            f"درجه فعلی: {'⭐'*current}{'☆'*(5-current)} ({current}/5)\n\n"
            f"{desc}\n\n"
            f"روی درجه مورد نظر بزن:",
            reply_markup=_pers_kb(chat_id, current)
        )
        return

    if action == "set_pers":
        value = int(parts[3])
        await db.set_group_settings(chat_id, ai_personality=value)
        await cq.answer(f"✅ شخصیت: {'⭐'*value}{'☆'*(5-value)} ({value}/5)", show_alert=False)
        s = await db.get_group_settings(chat_id)
        await cq.message.edit_text(_ai_panel_text(s), reply_markup=_ai_panel_kb(s, chat_id))
        return

    # ─── Back to main ───
    if action == "main":
        s = await db.get_group_settings(chat_id)
        await cq.message.edit_text(_main_text(s), reply_markup=_main_kb(s, chat_id))
        return

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
