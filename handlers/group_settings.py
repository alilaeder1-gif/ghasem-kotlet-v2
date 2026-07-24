from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command
from database import db

router = Router()


def _settings_kb(settings: dict) -> InlineKeyboardBuilder:
    b = InlineKeyboardBuilder()
    ai = settings.get("ai_chat_enabled", True)
    spam = settings.get("spam_protection", True)
    flood = settings.get("flood_protection", True)
    welcome = settings.get("welcome_enabled", True)
    linkdel = settings.get("link_delete_enabled", False)
    forcesub = settings.get("force_sub_enabled", False)

    b.button(text=f"{'✅' if ai else '❌'} هوش مصنوعی", callback_data="st_ai")
    b.button(text=f"{'✅' if spam else '❌'} محافظت اسپم", callback_data="st_spam")
    b.button(text=f"{'✅' if flood else '❌'} محافظت سیل", callback_data="st_flood")
    b.button(text=f"{'✅' if welcome else '❌'} خوشامدگویی", callback_data="st_welcome")
    b.button(text=f"{'✅' if linkdel else '❌'} حذف لینک", callback_data="st_linkdel")
    b.button(text=f"{'✅' if forcesub else '❌'} عضویت اجباری", callback_data="st_forcesub")
    b.button(text="🔗 تنظیم حذف لینک", callback_data="st_linkdel_set")
    b.adjust(2)
    return b


@router.message(Command("settings", "set", "تنظیمات", "تنظیم"))
async def show_settings(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        return
    chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status not in ("creator", "administrator"):
        return await message.reply("❌ فقط ادمین‌ها دسترسی دارن.")

    settings = await db.get_group_settings(message.chat.id)
    if not settings:
        return await message.reply("❌ خطا در دریافت تنظیمات.")

    b = _settings_kb(settings)
    await message.reply(
        "⚙️ **پنل مدیریت تنظیمات گروه**\n\n"
        "روی هر دکمه کلیک کن تا وضعیت تغییر کنه.",
        reply_markup=b.as_markup()
    )


@router.callback_query(F.data.startswith("st_"))
async def settings_callback(cq: CallbackQuery):
    try:
        chat_member = await cq.bot.get_chat_member(cq.message.chat.id, cq.from_user.id)
        if chat_member.status not in ("creator", "administrator"):
            return await cq.answer("❌ فقط ادمین‌ها می‌تونن.", show_alert=True)
    except Exception:
        return await cq.answer("❌ خطا", show_alert=True)

    action = cq.data.split("_", 1)[1]
    chat_id = cq.message.chat.id

    if action == "ai":
        s = await db.get_group_settings(chat_id)
        cur = s.get("ai_chat_enabled", True) if s else True
        await db.update_group_settings(chat_id, ai_chat_enabled=int(not cur))
        await cq.answer(f"هوش مصنوعی {'✅ فعال' if not cur else '❌ غیرفعال'} شد.", show_alert=False)

    elif action == "spam":
        s = await db.get_group_settings(chat_id)
        cur = s.get("spam_protection", True) if s else True
        await db.update_group_settings(chat_id, spam_protection=int(not cur))
        await cq.answer(f"محافظت اسپم {'✅ فعال' if not cur else '❌ غیرفعال'} شد.", show_alert=False)

    elif action == "flood":
        s = await db.get_group_settings(chat_id)
        cur = s.get("flood_protection", True) if s else True
        await db.update_group_settings(chat_id, flood_protection=int(not cur))
        await cq.answer(f"محافظت سیل {'✅ فعال' if not cur else '❌ غیرفعال'} شد.", show_alert=False)

    elif action == "welcome":
        s = await db.get_group_settings(chat_id)
        cur = s.get("welcome_enabled", True) if s else True
        await db.update_group_settings(chat_id, welcome_enabled=int(not cur))
        await cq.answer(f"خوشامدگویی {'✅ فعال' if not cur else '❌ غیرفعال'} شد.", show_alert=False)

    elif action == "linkdel":
        s = await db.get_group_settings(chat_id)
        cur = s.get("link_delete_enabled", False) if s else False
        await db.update_group_settings(chat_id, link_delete_enabled=int(not cur))
        await cq.answer(f"حذف لینک {'✅ فعال' if not cur else '❌ غیرفعال'} شد.", show_alert=False)

    elif action == "forcesub":
        s = await db.get_group_settings(chat_id)
        cur = s.get("force_sub_enabled", False) if s else False
        await db.update_group_settings(chat_id, force_sub_enabled=int(not cur))
        await cq.answer(f"عضویت اجباری {'✅ فعال' if not cur else '❌ غیرفعال'} شد.", show_alert=False)

    elif action == "linkdel_set":
        await cq.message.reply(
            "🔗 **تنظیم حذف لینک**\n\n"
            "برای تنظیم از دستور زیر استفاده کن:\n"
            "`/linkdelete on` - حذف فوری همه لینک‌ها\n"
            "`/linkdelete 30` - حذف لینک تا ۳۰ دقیقه بعد جوین\n"
            "`/linkdelete off` - غیرفعال کردن\n\n"
            "عدد به معنی دقیقه هست (۰ = فوری)."
        )
        return

    # refresh the keyboard
    s = await db.get_group_settings(chat_id)
    if s:
        b = _settings_kb(s)
        await cq.message.edit_reply_markup(reply_markup=b.as_markup())
