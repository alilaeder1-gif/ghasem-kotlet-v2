import json
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command
from database import db

router = Router()
_pending = {}

# ─── Helper: pagination ───
def _paginate(buttons, page=0, per_page=6, back_cb=None):
    b = InlineKeyboardBuilder()
    start = page * per_page
    end = start + per_page
    for btn in buttons[start:end]:
        b.button(text=btn[0], callback_data=btn[1])
    if len(buttons) > per_page:
        nav = InlineKeyboardBuilder()
        if page > 0:
            nav.button(text="◀️ قبلی", callback_data=f"sp_page|{back_cb}|{page-1}")
        if end < len(buttons):
            nav.button(text="بعدی ▶️", callback_data=f"sp_page|{back_cb}|{page+1}")
        nav.button(text="🔙 برگشت", callback_data=back_cb)
        b.adjust(2)
        return b.attach(nav).as_markup()
    b.button(text="🔙 برگشت", callback_data=back_cb)
    b.adjust(2)
    return b.as_markup()


# ═══════════════════════════════════════════════
#  MAIN SETTINGS PANEL
# ═══════════════════════════════════════════════

async def show_main(msg_or_cq, chat_id, edit=True):
    s = await db.get_group_settings(chat_id)
    ai_st = '🟢' if s.get('ai_chat_enabled', True) else '🔴'
    sp_st = '🟢' if s.get('spam_protection', True) else '🔴'
    fl_st = '🟢' if s.get('flood_protection', True) else '🔴'
    wc_st = '🟢' if s.get('welcome_enabled', True) else '🔴'
    lk_st = '🟢' if s.get('link_delete_enabled', False) else '🔴'
    fs_st = '🟢' if s.get('force_sub_enabled', False) else '🔴'
    beh_name = _AI_BEHAVIOR_NAMES.get(s.get("ai_behavior", "default"))
    tone_name = _AI_TONE_NAMES.get(s.get("ai_tone", "tehrani"))
    pers = s.get("ai_personality", 3)
    text = (
        f"⚙️ **پنل تنظیمات گروه**\n"
        f"╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌\n"
        f"{ai_st} **هوش مصنوعی** {ai_st}\n"
        f"{sp_st} **ضد اسپم** {sp_st}\n"
        f"{fl_st} **ضد سیل (Flood)** {fl_st}\n"
        f"{wc_st} **خوشامدگویی** {wc_st}\n"
        f"{lk_st} **حذف خودکار لینک** {lk_st}\n"
        f"{fs_st} **عضویت اجباری** {fs_st}\n"
        f"╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌\n"
        f"🎭 شخصیت: {beh_name} | {tone_name} | {'⭐'*pers}\n\n"
        f"برای تنظیم هر بخش روی دکمه‌اش بزن 👇"
    )
    b = InlineKeyboardBuilder()
    b.button(text=f"{ai_st} 🤖 هوش مصنوعی", callback_data=f"sp|ai_set|{chat_id}")
    b.button(text=f"{sp_st} 🛡️ ضد اسپم", callback_data=f"sp|spam_set|{chat_id}")
    b.button(text=f"{fl_st} 🌊 ضد سیل", callback_data=f"sp|flood_set|{chat_id}")
    b.button(text=f"{wc_st} 👋 خوشامدگویی", callback_data=f"sp|welcome_set|{chat_id}")
    b.button(text=f"{lk_st} 🔗 حذف لینک", callback_data=f"sp|link_set|{chat_id}")
    b.button(text=f"{fs_st} 📣 عضویت اجباری", callback_data=f"sp|forcesub_set|{chat_id}")
    b.button(text=f"🎭 شخصیت: {beh_name}", callback_data=f"sp|ai_personality|{chat_id}")
    b.adjust(2)
    kb = b.as_markup()
    if edit:
        await msg_or_cq.message.edit_text(text, reply_markup=kb)
    else:
        await msg_or_cq.reply(text, reply_markup=kb)

# ═══════════════════════════════════════════════
#  AI SETTINGS PAGE (on/off + description)
# ═══════════════════════════════════════════════

async def show_ai_settings(msg_or_cq, chat_id):
    s = await db.get_group_settings(chat_id)
    enabled = s.get("ai_chat_enabled", True)
    text = (
        f"🤖 **تنظیمات هوش مصنوعی**\n"
        f"╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌\n"
        f"وضعیت: {'🟢 فعال' if enabled else '🔴 غیرفعال'}\n\n"
        f"هوش مصنوعی کتلت به پیام‌های کاربران جواب میده. "
        f"میتونه سوالات عمومی جواب بده، شوخی کنه، کد بنویسه و نقاشی بکشه.\n\n"
        f"📎 **روش استفاده:**\n"
        f"• به بات منشن کن: `@kotletaiBot پیام`\n"
        f"• روی پیام بات ریپلای کن\n"
        f"• اسم کتلت رو تو پیام بنویس\n\n"
        f"📌 **دستورات مرتبط:**\n"
        f"• `/draw` 🎨 نقاشی با هوش مصنوعی\n"
        f"• `/code` 💻 کدنویسی\n"
        f"• `/toggleai` 🔄 روشن/خاموش سریع"
    )
    b = InlineKeyboardBuilder()
    b.button(text=f"{'🔴 غیرفعال' if enabled else '🟢 فعال'} کردن هوش مصنوعی", callback_data=f"sp|ai_toggle|{chat_id}")
    b.button(text="🔙 بازگشت به تنظیمات", callback_data=f"sp|main|{chat_id}")
    b.adjust(1)
    await msg_or_cq.message.edit_text(text, reply_markup=b.as_markup())

# ═══════════════════════════════════════════════
#  AI PERSONALITY SUB-PAGE
# ═══════════════════════════════════════════════

_AI_BEHAVIORS = ["default", "friendly", "formal", "funny", "cool", "polite", "rude"]
_AI_BEHAVIOR_NAMES = {"default":"پیش‌فرض","friendly":"دوستانه","formal":"رسمی","funny":"شوخ","cool":"باحال","polite":"مودب","rude":"بی‌ادب"}
_AI_BEHAVIOR_DESC = {
    "default":"رفتار پیش‌فرض کتلت", "friendly":"گرم و صمیمی با همه",
    "formal":"مودب و محترم", "funny":"شوخ و بامزه",
    "cool":"جوون‌پسند و امروزی", "polite":"باادب و مؤدب",
    "rude":"گستاخ و توهین‌آمیز"
}
_AI_TONES = ["tehrani", "turkish", "kurdish", "gilaki", "normal"]
_AI_TONE_NAMES = {"tehrani":"تهرونی","turkish":"ترکی","kurdish":"کردی","gilaki":"گیلکی","normal":"معمولی"}
_AI_TONE_DESC = {
    "tehrani":"با لحن تهرونی خیابونی", "turkish":"با کلمات ترکی آذربایجانی",
    "kurdish":"با اصطلاحات کردی", "gilaki":"با لحن گیلکی رشتی", "normal":"معمولی و ساده"
}

async def show_ai_personality(msg_or_cq, chat_id):
    s = await db.get_group_settings(chat_id)
    beh = s.get("ai_behavior", "default")
    tone = s.get("ai_tone", "tehrani")
    pers = s.get("ai_personality", 3)
    pers_desc = {1:"🤖 رباتی خشک", 2:"😐 معمولی", 3:"😊 خودمونی", 4:"😂 باحال", 5:"🔥 پررو"}
    text = (
        f"🧠 **تنظیمات شخصیت هوش مصنوعی**\n\n"
        f"🎭 **رفتار:** {_AI_BEHAVIOR_NAMES.get(beh, beh)}\n"
        f"🎙 **لحن:** {_AI_TONE_NAMES.get(tone, tone)}\n"
        f"💪 **شخصیت:** {'⭐'*pers}{'☆'*(5-pers)} ({pers}/5 - {pers_desc[pers]})\n\n"
        f"برای تغییر روی دکمه بزن 👇"
    )
    b = InlineKeyboardBuilder()
    b.button(text=f"🎭 رفتار: {_AI_BEHAVIOR_NAMES.get(beh, beh)}", callback_data=f"sp|ai_beh_list|{chat_id}")
    b.button(text=f"🎙️ لحن: {_AI_TONE_NAMES.get(tone, tone)}", callback_data=f"sp|ai_tone_list|{chat_id}")
    b.button(text=f"💪 شخصیت: {'⭐'*pers}{'☆'*(5-pers)} ({pers}/5)", callback_data=f"sp|ai_pers_list|{chat_id}")
    b.button(text="🔙 بازگشت به تنظیمات", callback_data=f"sp|main|{chat_id}")
    b.adjust(1)
    await msg_or_cq.message.edit_text(text, reply_markup=b.as_markup())

_BEH_EMOJI = {"default":"⚙️","friendly":"🤗","formal":"🎩","funny":"😂","cool":"😎","polite":"🙏","rude":"🤬"}

async def show_ai_behaviors(msg_or_cq, chat_id):
    s = await db.get_group_settings(chat_id)
    cur = s.get("ai_behavior", "default")
    text = f"🎭 **انتخاب حالت رفتار**\n╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌\n"
    for k in _AI_BEHAVIORS:
        emo = _BEH_EMOJI.get(k, "")
        mark = "✅ " if k == cur else "   "
        text += f"{mark}{emo} {_AI_BEHAVIOR_NAMES[k]}: {_AI_BEHAVIOR_DESC[k]}\n"
    text += "\nروی حالت مورد نظر بزن 👇"
    b = InlineKeyboardBuilder()
    for k in _AI_BEHAVIORS:
        emo = _BEH_EMOJI.get(k, "")
        sel = f"✅ {emo} " if k == cur else f"{emo} "
        b.button(text=f"{sel}{_AI_BEHAVIOR_NAMES[k]}", callback_data=f"sp|set_ai_beh|{k}|{chat_id}")
    b.button(text="🔙 بازگشت", callback_data=f"sp|ai_personality|{chat_id}")
    b.adjust(2)
    await msg_or_cq.message.edit_text(text, reply_markup=b.as_markup())

_TONE_EMOJI = {"tehrani":"🏙️","turkish":"🌋","kurdish":"⛰️","gilaki":"🌿","normal":"💬"}

async def show_ai_tones(msg_or_cq, chat_id):
    s = await db.get_group_settings(chat_id)
    cur = s.get("ai_tone", "tehrani")
    text = f"🎙️ **انتخاب لحن گفتار**\n╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌\n"
    for k in _AI_TONES:
        emo = _TONE_EMOJI.get(k, "")
        mark = "✅ " if k == cur else "   "
        text += f"{mark}{emo} {_AI_TONE_NAMES[k]}: {_AI_TONE_DESC[k]}\n"
    text += "\nروی لحن مورد نظر بزن 👇"
    b = InlineKeyboardBuilder()
    for k in _AI_TONES:
        emo = _TONE_EMOJI.get(k, "")
        sel = f"✅ {emo} " if k == cur else f"{emo} "
        b.button(text=f"{sel}{_AI_TONE_NAMES[k]}", callback_data=f"sp|set_ai_tone|{k}|{chat_id}")
    b.button(text="🔙 بازگشت", callback_data=f"sp|ai_personality|{chat_id}")
    b.adjust(2)
    await msg_or_cq.message.edit_text(text, reply_markup=b.as_markup())

async def show_ai_pers_levels(msg_or_cq, chat_id):
    s = await db.get_group_settings(chat_id)
    cur = s.get("ai_personality", 3)
    pers_desc = {1:"🤖 رباتی خشک", 2:"😐 معمولی", 3:"😊 خودمونی گرم", 4:"😂 شوخ باحال", 5:"🔥 پررو بی‌پروا"}
    pers_emoji = {1:"🤖", 2:"😐", 3:"😊", 4:"😂", 5:"🔥"}
    text = f"💪 **درجه شخصیت**\n╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌\n"
    for i in range(1, 6):
        mark = "✅ " if i == cur else "   "
        text += f"{mark}{'⭐'*i}{'☆'*(5-i)} ({i}) {pers_desc[i]}\n"
    text += "\nروی درجه بزن 👇"
    b = InlineKeyboardBuilder()
    for i in range(1, 6):
        emo = pers_emoji[i]
        sel = f"✅ {emo} " if i == cur else f"{'⭐'*i}{'☆'*(5-i)} "
        b.button(text=f"{sel}({i})", callback_data=f"sp|set_ai_pers|{i}|{chat_id}")
    b.button(text="🔙 بازگشت", callback_data=f"sp|ai_personality|{chat_id}")
    b.adjust(2)
    await msg_or_cq.message.edit_text(text, reply_markup=b.as_markup())

# ═══════════════════════════════════════════════
#  SPAM SETTINGS PAGE
# ═══════════════════════════════════════════════

SPAM_PATTERN_GROUPS = {
    "links": "🔗 لینک‌های آلوده (bit.ly, t.me/+)",
    "ads": "📺 تبلیغات (تخفیف, رایگان, ویژه)",
    "crypto": "💎 ارز دیجیتال (بیت‌کوین, تتر, usdt)",
    "betting": "🎰 شرط‌بندی (کازینو, پیشبینی)",
    "dating": "💔 دوست‌یابی (سکسی, چت خصوصی)",
    "bot": "⚙️ ساخت ربات (bot father)",
}

async def show_spam_settings(msg_or_cq, chat_id):
    s = await db.get_group_settings(chat_id)
    cfg = s.get("spam_config", {})
    enabled = s.get("spam_protection", True)
    text = (
        f"🛡️ **تنظیمات محافظت اسپم**\n"
        f"╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌\n"
        f"وضعیت کلی: {'🟢 فعال' if enabled else '🔴 غیرفعال'}\n\n"
        f"اسپم‌ها به صورت خودکار تشخیص داده میشن و حذف میشن. "
        f"بعد از چند بار تکرار، کاربر بن یا میوت میشه.\n\n"
        f"**انواع اسپم قابل تشخیص:**\n"
    )
    for key, label in SPAM_PATTERN_GROUPS.items():
        on = cfg.get(key, True)
        text += f"  {'✅' if on else '❌'} {label}\n"
    text += "\nبرای فعال/غیرفعال کردن هر نوع اسپم، روی دکمه بزن 👇"
    btns = []
    for key, label in SPAM_PATTERN_GROUPS.items():
        on = cfg.get(key, True)
        btns.append((f"{'🟢 فعال' if on else '🔴 غیرفعال'} | {label}", f"sp|spam_toggle|{key}|{chat_id}"))
    btns.append((f"{'🔴 غیرفعال' if enabled else '🟢 فعال'} | اسپم کلی", f"sp|spam_onoff|{chat_id}"))
    btns.append(("🔙 برگشت", f"sp|main|{chat_id}"))
    await msg_or_cq.message.edit_text(text, reply_markup=_paginate(btns, back_cb=f"sp|main|{chat_id}"))

# ═══════════════════════════════════════════════
#  FLOOD SETTINGS PAGE
# ═══════════════════════════════════════════════

async def show_flood_settings(msg_or_cq, chat_id):
    s = await db.get_group_settings(chat_id)
    cfg = s.get("flood_config", {})
    enabled = s.get("flood_protection", True)
    limit = cfg.get("limit", 5)
    window = cfg.get("window", 3)
    action = cfg.get("action", "warn")
    action_names = {"warn":"⚠️ اخطار", "mute":"🔇 میوت", "ban":"🚫 بن"}
    text = (
        f"🌊 **تنظیمات محافظت سیل (Flood)**\n"
        f"╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌\n"
        f"وضعیت: {'🟢 فعال' if enabled else '🔴 غیرفعال'}\n\n"
        f"اگه کاربری چند پیام پشت سر هم بفرسته، تشخیص داده میشه.\n\n"
        f"📊 **تنظیمات فعلی:**\n"
        f"• محدودیت: **{limit}** پیام در **{window}** ثانیه\n"
        f"• عکس‌العمل: {action_names.get(action, action)}\n\n"
        f"📎 **دستور سریع:**\n"
        f"`/floodlimit <تعداد> <ثانیه>`"
    )
    b = InlineKeyboardBuilder()
    b.button(text=f"🔢 محدودیت: {limit} پیام", callback_data=f"sp|flood_limit|{chat_id}")
    b.button(text=f"⏱ پنجره: {window} ثانیه", callback_data=f"sp|flood_window|{chat_id}")
    b.button(text=f"⚡ عکس‌العمل: {action_names.get(action, action)}", callback_data=f"sp|flood_action|{chat_id}")
    b.button(text=f"{'🔴 غیرفعال' if enabled else '🟢 فعال'} کردن سیل", callback_data=f"sp|flood_onoff|{chat_id}")
    b.button(text="🔙 بازگشت به تنظیمات", callback_data=f"sp|main|{chat_id}")
    b.adjust(2)
    await msg_or_cq.message.edit_text(text, reply_markup=b.as_markup())

async def show_flood_limit(msg_or_cq, chat_id):
    s = await db.get_group_settings(chat_id)
    cfg = s.get("flood_config", {})
    cur = cfg.get("limit", 5)
    text = (
        f"🔢 **تعداد مجاز پیام**\n\n"
        f"حداکثر چند پیام کاربر می‌تونه بفرسته قبل از اینکه سیل محسوب بشه؟\n\n"
        f"مقدار فعلی: **{cur}**\n\n"
        f"روی مقدار جدید بزن 👇"
    )
    b = InlineKeyboardBuilder()
    for v in [3, 5, 7, 10, 15]:
        b.button(text=f"{'✅' if v==cur else ''} {v} پیام", callback_data=f"sp|set_flood_limit|{v}|{chat_id}")
    b.button(text="🔙 بازگشت", callback_data=f"sp|flood_set|{chat_id}")
    b.adjust(2)
    await msg_or_cq.message.edit_text(text, reply_markup=b.as_markup())

async def show_flood_window(msg_or_cq, chat_id):
    s = await db.get_group_settings(chat_id)
    cfg = s.get("flood_config", {})
    cur = cfg.get("window", 3)
    text = (
        f"⏱ **پنجره زمانی**\n\n"
        f"چند ثانیه به عنوان بازه زمانی در نظر گرفته بشه؟\n\n"
        f"مقدار فعلی: **{cur} ثانیه**\n\n"
        f"روی مقدار جدید بزن 👇"
    )
    b = InlineKeyboardBuilder()
    for v in [2, 3, 5, 10, 15]:
        b.button(text=f"{'✅' if v==cur else ''} {v} ثانیه", callback_data=f"sp|set_flood_window|{v}|{chat_id}")
    b.button(text="🔙 بازگشت", callback_data=f"sp|flood_set|{chat_id}")
    b.adjust(2)
    await msg_or_cq.message.edit_text(text, reply_markup=b.as_markup())

async def show_flood_action(msg_or_cq, chat_id):
    s = await db.get_group_settings(chat_id)
    cfg = s.get("flood_config", {})
    cur = cfg.get("action", "warn")
    actions = {"warn":"⚠️ اخطار", "mute":"🔇 میوت ۱ ساعته", "ban":"🚫 بن دائمی"}
    text = (
        f"⚡ **عکس‌العمل در برابر سیل**\n\n"
        f"وقتی کاربر سیل میفرسته، بات چه عکس‌العملی نشون بده؟\n\n"
        f"مقدار فعلی: **{actions.get(cur, cur)}**\n\n"
        f"روی گزینه جدید بزن 👇"
    )
    b = InlineKeyboardBuilder()
    for k, v in actions.items():
        b.button(text=f"{'✅' if k==cur else ''} {v}", callback_data=f"sp|set_flood_action|{k}|{chat_id}")
    b.button(text="🔙 بازگشت", callback_data=f"sp|flood_set|{chat_id}")
    b.adjust(2)
    await msg_or_cq.message.edit_text(text, reply_markup=b.as_markup())

# ═══════════════════════════════════════════════
#  WELCOME SETTINGS PAGE
# ═══════════════════════════════════════════════

async def show_welcome_settings(msg_or_cq, chat_id):
    s = await db.get_group_settings(chat_id)
    welcome = await db.get_welcome(chat_id)
    enabled = s.get("welcome_enabled", True)
    msg_text = welcome["message"] if welcome and welcome.get("message") else "سلام {name}! خوش اومدی به گروه 👋"
    text = (
        f"👋 **تنظیمات خوشامدگویی**\n"
        f"╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌\n"
        f"وضعیت: {'🟢 فعال' if enabled else '🔴 غیرفعال'}\n\n"
        f"📝 **پیام فعلی:**\n"
        f"`{msg_text[:200]}`\n\n"
        f"📌 **متغیرها:** `{{name}}` اسم | `{{group}}` گروه | `{{id}}` آیدی\n\n"
        f"👇 **روی یکی از قالب‌های آماده بزن** یا خودت بنویس:"
    )
    WELCOME_TEMPLATES = [
        ("سلام {name}! خوش اومدی به {group} 👋", "👋 ساده"),
        ("سلام {name} جوون! به گروه {group} خوش اومدی 😎", "😎 جوونی"),
        ("🥳 {name} عزیز به گروه {group} خوش اومدی!\nحتما قوانین رو با /rules بخون.", "🥳 رسمی"),
        ("سلام {name}! 😊\nبه جمع ما تو {group} خوش اومدی.\nاز فعالیتت لذت ببر! 🌟", "😊 گرم"),
        ("خوش اومدی {name} جان! 🎉\nبه گروه {group} خوش اومدی.\nاگه سوالی داری بپرس.", "🎉 خودمونی"),
    ]
    b = InlineKeyboardBuilder()
    for tmpl, label in WELCOME_TEMPLATES:
        b.button(text=label, callback_data=f"sp|welcome_template|{WELCOME_TEMPLATES.index((tmpl, label))}|{chat_id}")
    b.button(text="✏️ نوشتن متن دلخواه", callback_data=f"sp|welcome_edit|{chat_id}")
    b.button(text=f"{'🔴 غیرفعال' if enabled else '🟢 فعال'} کردن خوشامدگویی", callback_data=f"sp|welcome_onoff|{chat_id}")
    b.button(text="🔙 بازگشت به تنظیمات", callback_data=f"sp|main|{chat_id}")
    b.adjust(2)
    await msg_or_cq.message.edit_text(text, reply_markup=b.as_markup())


# ═══════════════════════════════════════════════
#  LINK DELETE SETTINGS PAGE
# ═══════════════════════════════════════════════

async def show_link_settings(msg_or_cq, chat_id):
    s = await db.get_group_settings(chat_id)
    cfg = s.get("link_config", {})
    enabled = s.get("link_delete_enabled", False)
    delay = s.get("link_delete_delay", 0)
    mode = cfg.get("mode", "all")
    mode_names = {"all":"همه لینک‌ها", "tme":"فقط t.me", "new":"کاربر جدید"}
    text = (
        f"🔗 **تنظیمات حذف خودکار لینک**\n"
        f"╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌\n"
        f"وضعیت: {'🟢 فعال' if enabled else '🔴 غیرفعال'}\n\n"
        f"پیام‌های حاوی لینک به صورت خودکار حذف میشن.\n\n"
        f"📊 **تنظیمات فعلی:**\n"
        f"• حالت: {mode_names.get(mode, mode)}\n"
        f"• تاخیر: {delay} دقیقه (بعد از جوین)\n\n"
        f"📎 **دستورات سریع:**\n"
        f"• `/linkdelete on` - حذف فوری\n"
        f"• `/linkdelete 30` - تا ۳۰ دقیقه\n"
        f"• `/linkdelete off` - غیرفعال"
    )
    b = InlineKeyboardBuilder()
    b.button(text=f"📋 حالت: {mode_names.get(mode, mode)}", callback_data=f"sp|link_mode|{chat_id}")
    b.button(text=f"⏱ تاخیر: {delay} دقیقه", callback_data=f"sp|link_delay|{chat_id}")
    b.button(text=f"{'🔴 غیرفعال' if enabled else '🟢 فعال'} کردن حذف لینک", callback_data=f"sp|link_onoff|{chat_id}")
    b.button(text="🔙 بازگشت به تنظیمات", callback_data=f"sp|main|{chat_id}")
    b.adjust(2)
    await msg_or_cq.message.edit_text(text, reply_markup=b.as_markup())

async def show_link_mode(msg_or_cq, chat_id):
    s = await db.get_group_settings(chat_id)
    cfg = s.get("link_config", {})
    cur = cfg.get("mode", "all")
    modes = {"all":"🌐 همه لینک‌ها (http, https, t.me)", "tme":"📡 فقط لینک تلگرام (t.me)", "new":"🆕 فقط کاربرای جدید (تا ۳۰ دقیقه)"}
    text = f"🔗 **نوع لینک‌های حذف شده**\n╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌\n\nمقدار فعلی: {modes.get(cur, cur)}\n\nروی گزینه جدید بزن 👇"
    b = InlineKeyboardBuilder()
    for k, v in modes.items():
        b.button(text=f"{'✅' if k==cur else ''} {v}", callback_data=f"sp|set_link_mode|{k}|{chat_id}")
    b.button(text="🔙 بازگشت", callback_data=f"sp|link_set|{chat_id}")
    b.adjust(2)
    await msg_or_cq.message.edit_text(text, reply_markup=b.as_markup())

async def show_link_delay(msg_or_cq, chat_id):
    s = await db.get_group_settings(chat_id)
    cur = s.get("link_delete_delay", 0)
    text = (
        f"⏱ **تاخیر حذف لینک**\n\n"
        f"چند دقیقه بعد از جوین شدن کاربر، لینک‌هاش حذف بشه؟\n"
        f"`0` یعنی فوری حذف بشه.\n\n"
        f"مقدار فعلی: **{cur} دقیقه**\n\n"
        f"روی مقدار بزن 👇"
    )
    b = InlineKeyboardBuilder()
    for v in [0, 5, 10, 30, 60, 120]:
        b.button(text=f"{'✅' if v==cur else ''} {v} دقیقه", callback_data=f"sp|set_link_delay|{v}|{chat_id}")
    b.button(text="🔙 بازگشت", callback_data=f"sp|link_set|{chat_id}")
    b.adjust(2)
    await msg_or_cq.message.edit_text(text, reply_markup=b.as_markup())

# ═══════════════════════════════════════════════
#  FORCE SUB SETTINGS PAGE
# ═══════════════════════════════════════════════

async def show_forcesub_settings(msg_or_cq, chat_id):
    s = await db.get_group_settings(chat_id)
    enabled = s.get("force_sub_enabled", False)
    channels = s.get("force_sub_config", s.get("force_sub_channel", ""))
    if isinstance(channels, str):
        channels = [{"username": channels, "label": "کانال", "emoji": "📢"}] if channels else []
    text = (
        f"📣 **تنظیمات عضویت اجباری**\n"
        f"╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌\n"
        f"وضعیت: {'🟢 فعال' if enabled else '🔴 غیرفعال'}\n\n"
        f"کاربران برای ارسال پیام در گروه، باید عضو کانال‌های مشخصی بشن.\n"
        f"میتونی چند تا کانال اضافه کنی.\n\n"
        f"📋 **کانال‌های فعلی:**\n"
    )
    if channels:
        for ch in channels:
            emoji = ch.get("emoji", "📢")
            label = ch.get("label", ch.get("username", ""))
            username = ch.get("username", "")
            text += f"  {emoji} {label} | @{username}\n"
    else:
        text += "  ❌ هیچ کانالی تنظیم نشده\n"
    text += (
        f"\n📎 **دستورات سریع:**\n"
        f"• `/forcesub @channel` - تنظیم کانال\n"
        f"• `/forcesub off` - غیرفعال"
    )
    btns = [("➕ افزودن کانال جدید", f"sp|forcesub_add|{chat_id}")]
    for i, ch in enumerate(channels):
        emoji = ch.get("emoji", "📢")
        label = ch.get("label", ch.get("username", ""))
        btns.append((f"✏️ {emoji} {label}", f"sp|forcesub_edit|{i}|{chat_id}"))
    btns.append((f"{'🔴 غیرفعال' if enabled else '🟢 فعال'} کردن عضویت اجباری", f"sp|forcesub_onoff|{chat_id}"))
    btns.append(("🔙 بازگشت به تنظیمات", f"sp|main|{chat_id}"))
    await msg_or_cq.message.edit_text(text, reply_markup=_paginate(btns, back_cb=f"sp|main|{chat_id}"))


# ═══════════════════════════════════════════════
#  MAIN CALLBACK ROUTER
# ═══════════════════════════════════════════════

@router.callback_query(F.data.startswith("sp|"))
async def settings_panel_cb(cq: CallbackQuery):
    parts = cq.data.split("|")
    action = parts[1]
    chat_id = int(parts[-1]) if parts[-1].lstrip("-").isdigit() else cq.message.chat.id

    try:
        cm = await cq.bot.get_chat_member(chat_id, cq.from_user.id)
        if cm.status not in ("creator", "administrator"):
            return await cq.answer("❌ فقط ادمین", show_alert=True)
    except:
        return await cq.answer("❌ خطا", show_alert=True)

    # ─── Navigation ───
    if action == "main":
        await show_main(cq, chat_id)
        return

    if action == "ai_set":
        await show_ai_settings(cq, chat_id)
        return

    if action == "ai_personality":
        await show_ai_personality(cq, chat_id)
        return

    if action == "ai_beh_list":
        await show_ai_behaviors(cq, chat_id)
        return

    if action == "ai_tone_list":
        await show_ai_tones(cq, chat_id)
        return

    if action == "ai_pers_list":
        await show_ai_pers_levels(cq, chat_id)
        return

    if action == "spam_set":
        await show_spam_settings(cq, chat_id)
        return

    if action == "flood_set":
        await show_flood_settings(cq, chat_id)
        return

    if action == "welcome_set":
        await show_welcome_settings(cq, chat_id)
        return

    if action == "link_set":
        await show_link_settings(cq, chat_id)
        return

    if action == "link_mode":
        await show_link_mode(cq, chat_id)
        return

    if action == "link_delay":
        await show_link_delay(cq, chat_id)
        return

    if action == "forcesub_set":
        await show_forcesub_settings(cq, chat_id)
        return

    if action == "flood_limit":
        await show_flood_limit(cq, chat_id)
        return

    if action == "flood_window":
        await show_flood_window(cq, chat_id)
        return

    if action == "flood_action":
        await show_flood_action(cq, chat_id)
        return

    # ─── Toggles ───
    if action == "ai_toggle":
        s = await db.get_group_settings(chat_id)
        cur = s.get("ai_chat_enabled", True)
        await db.set_group_settings(chat_id, ai_chat_enabled=int(not cur))
        await cq.answer(f"{'🟢 فعال' if not cur else '🔴 غیرفعال'} شد ✅", show_alert=False)
        await show_ai_settings(cq, chat_id)
        return

    if action == "spam_onoff":
        s = await db.get_group_settings(chat_id)
        cur = s.get("spam_protection", True)
        await db.set_group_settings(chat_id, spam_protection=int(not cur))
        await cq.answer(f"{'🟢 فعال' if not cur else '🔴 غیرفعال'} شد ✅", show_alert=False)
        await show_spam_settings(cq, chat_id)
        return

    if action == "flood_onoff":
        s = await db.get_group_settings(chat_id)
        cur = s.get("flood_protection", True)
        await db.set_group_settings(chat_id, flood_protection=int(not cur))
        await cq.answer(f"{'🟢 فعال' if not cur else '🔴 غیرفعال'} شد ✅", show_alert=False)
        await show_flood_settings(cq, chat_id)
        return

    if action == "welcome_onoff":
        s = await db.get_group_settings(chat_id)
        cur = s.get("welcome_enabled", True)
        await db.set_group_settings(chat_id, welcome_enabled=int(not cur))
        await cq.answer(f"{'🟢 فعال' if not cur else '🔴 غیرفعال'} شد ✅", show_alert=False)
        await show_welcome_settings(cq, chat_id)
        return

    if action == "welcome_template":
        idx = int(parts[2])
        WELCOME_TEMPLATES = [
            "سلام {name}! خوش اومدی به {group} 👋",
            "سلام {name} جوون! به گروه {group} خوش اومدی 😎",
            "🥳 {name} عزیز به گروه {group} خوش اومدی!\nحتما قوانین رو با /rules بخون.",
            "سلام {name}! 😊\nبه جمع ما تو {group} خوش اومدی.\nاز فعالیتت لذت ببر! 🌟",
            "خوش اومدی {name} جان! 🎉\nبه گروه {group} خوش اومدی.\nاگه سوالی داری بپرس.",
        ]
        if 0 <= idx < len(WELCOME_TEMPLATES):
            await db.set_welcome(chat_id, WELCOME_TEMPLATES[idx], True)
            await db.set_group_settings(chat_id, welcome_enabled=1)
            await cq.answer(f"✅ قالب {idx+1} ذخیره شد!", show_alert=False)
            await show_welcome_settings(cq, chat_id)
        return

    if action == "link_onoff":
        s = await db.get_group_settings(chat_id)
        cur = s.get("link_delete_enabled", False)
        await db.set_group_settings(chat_id, link_delete_enabled=int(not cur))
        await cq.answer(f"{'🟢 فعال' if not cur else '🔴 غیرفعال'} شد ✅", show_alert=False)
        await show_link_settings(cq, chat_id)
        return

    if action == "forcesub_onoff":
        s = await db.get_group_settings(chat_id)
        cur = s.get("force_sub_enabled", False)
        await db.set_group_settings(chat_id, force_sub_enabled=int(not cur))
        await cq.answer(f"{'🟢 فعال' if not cur else '🔴 غیرفعال'} شد ✅", show_alert=False)
        await show_forcesub_settings(cq, chat_id)
        return

    # ─── Set values ───
    if action == "set_ai_beh":
        val = parts[2]
        await db.set_group_settings(chat_id, ai_behavior=val)
        await cq.answer(f"✅ رفتار: {_AI_BEHAVIOR_NAMES.get(val, val)}", show_alert=False)
        await show_ai_personality(cq, chat_id)
        return

    if action == "set_ai_tone":
        val = parts[2]
        await db.set_group_settings(chat_id, ai_tone=val)
        await cq.answer(f"✅ لحن: {_AI_TONE_NAMES.get(val, val)}", show_alert=False)
        await show_ai_personality(cq, chat_id)
        return

    if action == "set_ai_pers":
        val = int(parts[2])
        await db.set_group_settings(chat_id, ai_personality=val)
        await cq.answer(f"✅ شخصیت: {val}/5", show_alert=False)
        await show_ai_personality(cq, chat_id)
        return

    if action == "spam_toggle":
        key = parts[2]
        s = await db.get_group_settings(chat_id)
        cfg = s.get("spam_config", {}).copy()
        cfg[key] = not cfg.get(key, True)
        await db.set_group_settings(chat_id, spam_config=cfg)
        status = "✅ فعال" if cfg[key] else "❌ غیرفعال"
        await cq.answer(f"{SPAM_PATTERN_GROUPS.get(key, key)}: {status}", show_alert=False)
        await show_spam_settings(cq, chat_id)
        return

    if action == "set_flood_limit":
        val = int(parts[2])
        s = await db.get_group_settings(chat_id)
        cfg = s.get("flood_config", {}).copy()
        cfg["limit"] = val
        await db.set_group_settings(chat_id, flood_config=cfg)
        await cq.answer(f"✅ محدودیت: {val}", show_alert=False)
        await show_flood_settings(cq, chat_id)
        return

    if action == "set_flood_window":
        val = int(parts[2])
        s = await db.get_group_settings(chat_id)
        cfg = s.get("flood_config", {}).copy()
        cfg["window"] = val
        await db.set_group_settings(chat_id, flood_config=cfg)
        await cq.answer(f"✅ پنجره: {val} ثانیه", show_alert=False)
        await show_flood_settings(cq, chat_id)
        return

    if action == "set_flood_action":
        val = parts[2]
        s = await db.get_group_settings(chat_id)
        cfg = s.get("flood_config", {}).copy()
        cfg["action"] = val
        await db.set_group_settings(chat_id, flood_config=cfg)
        await cq.answer(f"✅ عکس‌العمل: {val}", show_alert=False)
        await show_flood_settings(cq, chat_id)
        return

    if action == "set_link_mode":
        val = parts[2]
        s = await db.get_group_settings(chat_id)
        cfg = s.get("link_config", {}).copy()
        cfg["mode"] = val
        await db.set_group_settings(chat_id, link_config=cfg)
        await cq.answer(f"✅ حالت: {val}", show_alert=False)
        await show_link_settings(cq, chat_id)
        return

    if action == "set_link_delay":
        val = int(parts[2])
        await db.set_group_settings(chat_id, link_delete_delay=val)
        await cq.answer(f"✅ تاخیر: {val} دقیقه", show_alert=False)
        s = await db.get_group_settings(chat_id)
        cfg = s.get("link_config", {}).copy()
        cfg["mode"] = cfg.get("mode", "all")
        await db.set_group_settings(chat_id, link_config=cfg)
        await show_link_settings(cq, chat_id)
        return

    if action == "welcome_edit":
        _pending[cq.from_user.id] = ("welcome_text", chat_id)
        await cq.message.reply(
            f"✏️ **متن جدید خوشامد رو بفرست.**\n\n"
            f"می‌تونی از این متغیرها استفاده کنی:\n"
            f"`{{name}}` - اسم کاربر\n"
            f"`{{group}}` - اسم گروه\n"
            f"`{{id}}` - آیدی کاربر\n\n"
            f"مثال: `سلام {{{{name}}}}! خوش اومدی به {{{{group}}}} 👋`\n\n"
            f"برای لغو، /cancel بزن."
        )
        return

    if action == "forcesub_add":
        _pending[cq.from_user.id] = ("forcesub_add", chat_id)
        await cq.message.reply(
            "➕ **افزودن کانال جدید برای عضویت اجباری**\n\n"
            "لطفاً به این فرمت بفرست:\n"
            "`@username | اسم دکمه | ایموجی`\n\n"
            "مثال:\n"
            "`@mychannel | کانال اصلی | 📢`\n\n"
            "برای لغو /cancel بزن."
        )
        return

    if action.startswith("forcesub_edit"):
        idx = int(parts[2])
        _pending[cq.from_user.id] = ("forcesub_edit", chat_id, idx)
        s = await db.get_group_settings(chat_id)
        channels = s.get("force_sub_config", [])
        if isinstance(channels, str):
            channels = []
        if idx < len(channels):
            ch = channels[idx]
            await cq.message.reply(
                f"✏️ **ویرایش کانال**\n\n"
                f"فعلی: {ch.get('emoji','📢')} {ch.get('label','')} - @{ch.get('username','')}\n\n"
                f"فرمت جدید:\n"
                f"`@username | اسم جدید | ایموجی جدید`\n\n"
                f"برای حذف این کانال: /delete_forcesub\n"
                f"برای لغو /cancel بزن."
            )
        return

    # ─── Pagination ───
    if action == "page":
        back_cb = "|".join(parts[2:-1])
        page = int(parts[-1])
        # re-render the current page with new page number
        # this is handled by _paginate - just update the message with the back action
        pass


# ─── Text input handlers ───

@router.message(F.text)
async def settings_text_handler(message: Message):
    if message.from_user.id not in _pending:
        return

    data = _pending[message.from_user.id]
    action = data[0]
    chat_id = data[1]

    if action == "welcome_text":
        await db.set_welcome(chat_id, message.text, True)
        await db.set_group_settings(chat_id, welcome_enabled=1)
        del _pending[message.from_user.id]
        await message.reply("✅ **پیام خوشامد تنظیم شد.**", reply_to_message_id=message.message_id)
        return

    if action == "forcesub_add":
        parts = [p.strip() for p in message.text.split("|")]
        if len(parts) < 1:
            return await message.reply("❌ فرمت اشتباه. باید: `@username | اسم | ایموجی`")
        username = parts[0].lstrip("@")
        label = parts[1] if len(parts) > 1 else username
        emoji = parts[2] if len(parts) > 2 else "📢"
        s = await db.get_group_settings(chat_id)
        channels = list(s.get("force_sub_config", []))
        if isinstance(channels, str):
            channels = []
        channels.append({"username": username, "label": label, "emoji": emoji})
        await db.set_group_settings(chat_id, force_sub_config=channels, force_sub_enabled=1)
        del _pending[message.from_user.id]
        await message.reply(f"✅ کانال {emoji} {label} اضافه شد.", reply_to_message_id=message.message_id)
        return

    if action == "forcesub_edit":
        idx = data[2]
        parts = [p.strip() for p in message.text.split("|")]
        if len(parts) < 1:
            return await message.reply("❌ فرمت اشتباه. باید: `@username | اسم | ایموجی`")
        username = parts[0].lstrip("@")
        label = parts[1] if len(parts) > 1 else username
        emoji = parts[2] if len(parts) > 2 else "📢"
        s = await db.get_group_settings(chat_id)
        channels = list(s.get("force_sub_config", []))
        if isinstance(channels, str):
            channels = []
        if idx < len(channels):
            channels[idx] = {"username": username, "label": label, "emoji": emoji}
            await db.set_group_settings(chat_id, force_sub_config=channels)
            del _pending[message.from_user.id]
            await message.reply(f"✅ کانال {emoji} {label} ویرایش شد.", reply_to_message_id=message.message_id)
        return

    if message.text.startswith("/delete_forcesub") and action == "forcesub_edit":
        idx = data[2]
        s = await db.get_group_settings(chat_id)
        channels = list(s.get("force_sub_config", []))
        if isinstance(channels, str):
            channels = []
        if idx < len(channels):
            ch = channels.pop(idx)
            await db.set_group_settings(chat_id, force_sub_config=channels)
            del _pending[message.from_user.id]
            await message.reply(f"✅ کانال {ch.get('emoji','📢')} {ch.get('label','')} حذف شد.", reply_to_message_id=message.message_id)
        return

    await message.reply("❌ دستور نامعتبر. /cancel بزنید.")
