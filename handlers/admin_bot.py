from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import db
from config import ADMIN_IDS

router = Router()


def _menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="👥 لیست گروه‌ها", callback_data="admin_groups")
    b.button(text="👤 لیست کاربران", callback_data="admin_users")
    b.button(text="📌 جزئیات گروه", callback_data="admin_g")
    b.button(text="✉️ ارسال پیام", callback_data="admin_gmsg")
    b.button(text="📋 تاریخچه گروه", callback_data="admin_ghistory")
    b.button(text="🔄 وضعیت AI", callback_data="admin_gtoggle")
    b.button(text="🚪 خروج از گروه", callback_data="admin_gleave")
    b.adjust(2)
    return b.as_markup()


def _back_btn() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔙 برگشت", callback_data="admin_back")
    return b.as_markup()


async def _group_list_kb(action: str, page: int = 0) -> InlineKeyboardMarkup:
    groups = await db.get_all_groups()
    per_page = 8
    total = len(groups)
    start = page * per_page
    end = start + per_page
    page_groups = groups[start:end]
    b = InlineKeyboardBuilder()
    for g in page_groups:
        title = (g["title"] or "بدون نام")[:20]
        b.button(text=f"{title}", callback_data=f"{action}_{g['chat_id']}")
    b.adjust(2)
    nav = InlineKeyboardBuilder()
    if page > 0:
        nav.button(text="◀️ قبلی", callback_data=f"admin_page|{action}|{page-1}")
    if end < total:
        nav.button(text="بعدی ▶️", callback_data=f"admin_page|{action}|{page+1}")
    nav.button(text="🔙 برگشت", callback_data="admin_back")
    return b.attach(nav).as_markup()


# ─── منوی اصلی ───

@router.message(F.text == "/ghasemkotlet")
async def admin_menu(message: Message):
    if message.chat.type != "private":
        return
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer("🔐 **پنل مدیریت بات**", reply_markup=_menu_kb())


@router.callback_query(F.data == "admin_back")
async def cb_back(cq: CallbackQuery):
    if cq.from_user.id not in ADMIN_IDS:
        return await cq.answer("❌ دسترسی نداری", show_alert=True)
    await cq.message.edit_text("🔐 **پنل مدیریت بات**", reply_markup=_menu_kb())


# ─── لیست گروه‌ها ───

@router.callback_query(F.data == "admin_groups")
async def cb_groups(cq: CallbackQuery):
    if cq.from_user.id not in ADMIN_IDS:
        return await cq.answer("❌ دسترسی نداری", show_alert=True)
    groups = await db.get_all_groups()
    if not groups:
        return await cq.message.edit_text("❌ هیچ گروهی نیست.", reply_markup=_back_btn())
    text = f"📋 **لیست گروه‌ها** ({len(groups)})\n\n"
    for i, g in enumerate(groups, 1):
        text += f"{i}. {g['title']}\n   👥 {g['members']} | 🆔 `{g['chat_id']}`\n\n"
    await cq.message.edit_text(text[:4000], reply_markup=_back_btn())


# ─── لیست کاربران ───

@router.callback_query(F.data == "admin_users")
async def cb_users(cq: CallbackQuery):
    if cq.from_user.id not in ADMIN_IDS:
        return await cq.answer("❌ دسترسی نداری", show_alert=True)
    users = await db.get_all_users()
    if not users:
        return await cq.message.edit_text("❌ هیچ کاربری نیست.", reply_markup=_back_btn())
    text = f"👤 **کاربران** ({len(users)})\n\n"
    for u in users[:30]:
        name = u["full_name"] or u["username"] or f"کاربر {u['user_id']}"
        joined = (u["first_seen"] or "نامشخص")[:10]
        text += f"• {name}\n  🆔 `{u['user_id']}` | 🏘 {u['groups']} گروه | 📅 {joined}\n\n"
    await cq.message.edit_text(text[:4000], reply_markup=_back_btn())


# ─── جزئیات گروه (انتخاب گروه) ───

@router.callback_query(F.data == "admin_g")
async def cb_g_ask(cq: CallbackQuery):
    if cq.from_user.id not in ADMIN_IDS:
        return await cq.answer("❌ دسترسی نداری", show_alert=True)
    groups = await db.get_all_groups()
    if not groups:
        return await cq.message.edit_text("❌ هیچ گروهی نیست.", reply_markup=_back_btn())
    await cq.message.edit_text("📌 **کدوم گروه؟**", reply_markup=await _group_list_kb("admin_g_sel"))


@router.callback_query(F.data.startswith("admin_g_sel_"))
async def cb_g_show(cq: CallbackQuery):
    if cq.from_user.id not in ADMIN_IDS:
        return await cq.answer("❌ دسترسی نداری", show_alert=True)
    try:
        chat_id = int(cq.data.split("_")[-1])
    except:
        return await cq.answer("❌ خطا", show_alert=True)
    groups = await db.get_all_groups()
    g = next((x for x in groups if x["chat_id"] == chat_id), None)
    if not g:
        return await cq.answer("❌ گروه پیدا نشد", show_alert=True)
    settings = await db.get_group_settings(chat_id)
    ai_status = "✅ فعال" if not settings or settings.get("ai_chat_enabled", True) else "❌ غیرفعال"
    spam_status = "✅ فعال" if not settings or settings.get("spam_protection", True) else "❌ غیرفعال"
    flood_status = "✅ فعال" if not settings or settings.get("flood_protection", True) else "❌ غیرفعال"
    force_sub_status = "✅ فعال" if settings and settings.get("force_sub_enabled") else "❌ غیرفعال"
    force_sub_ch = f" @{settings['force_sub_channel']}" if settings and settings.get("force_sub_channel") else ""
    b = InlineKeyboardBuilder()
    b.button(text="🔄 تغییر وضعیت AI", callback_data=f"admin_g_gtoggle_{chat_id}")
    b.button(text=f"🛡 اسپم: {spam_status}", callback_data=f"admin_g_spam_{chat_id}")
    b.button(text=f"🌊 سیل: {flood_status}", callback_data=f"admin_g_flood_{chat_id}")
    b.button(text=f"📢 عضویت اجباری: {force_sub_status}", callback_data=f"admin_g_forcesub_{chat_id}")
    b.button(text="📋 تاریخچه", callback_data=f"admin_g_ghistory_{chat_id}")
    b.button(text="✉️ ارسال پیام", callback_data=f"admin_g_gmsg_{chat_id}")
    b.button(text="🚪 خروج از گروه", callback_data=f"admin_g_gleave_{chat_id}")
    b.button(text="🔙 برگشت", callback_data="admin_g")
    b.adjust(2)
    await cq.message.edit_text(
        f"📌 **{g['title']}**\n"
        f"🆔 `{g['chat_id']}`\n"
        f"👥 اعضا: {g['members']}\n"
        f"🤖 AI: {ai_status}\n"
        f"🛡 محافظت اسپم: {spam_status}\n"
        f"🌊 محافظت سیل: {flood_status}\n"
        f"📢 عضویت اجباری: {force_sub_status}{force_sub_ch}",
        reply_markup=b.as_markup()
    )


@router.callback_query(F.data.startswith("admin_g_gtoggle_"))
async def cb_g_detail_toggle(cq: CallbackQuery):
    if cq.from_user.id not in ADMIN_IDS:
        return await cq.answer("❌ دسترسی نداری", show_alert=True)
    chat_id = int(cq.data.split("_")[-1])
    persona = await db.get_persona(chat_id)
    if persona:
        new_status = not persona["enabled"]
        await db.toggle_persona(chat_id, new_status)
        status = "✅ فعال" if new_status else "❌ غیرفعال"
    else:
        await db.set_persona(chat_id, "کُتلت", "تو یک ربات هوشمند هستی.")
        status = "✅ فعال"
    await cq.answer(f"AI {status} شد.", show_alert=False)
    await cb_g_show(cq)


@router.callback_query(F.data.startswith("admin_g_spam_"))
async def cb_g_toggle_spam(cq: CallbackQuery):
    if cq.from_user.id not in ADMIN_IDS:
        return await cq.answer("❌ دسترسی نداری", show_alert=True)
    chat_id = int(cq.data.split("_")[-1])
    settings = await db.get_group_settings(chat_id)
    current = settings.get("spam_protection", True) if settings else True
    await db.update_group_settings(chat_id, spam_protection=int(not current))
    await cq.answer(f"محافظت اسپم {'✅ فعال' if not current else '❌ غیرفعال'} شد.", show_alert=False)
    await cb_g_show(cq)


@router.callback_query(F.data.startswith("admin_g_flood_"))
async def cb_g_toggle_flood(cq: CallbackQuery):
    if cq.from_user.id not in ADMIN_IDS:
        return await cq.answer("❌ دسترسی نداری", show_alert=True)
    chat_id = int(cq.data.split("_")[-1])
    settings = await db.get_group_settings(chat_id)
    current = settings.get("flood_protection", True) if settings else True
    await db.update_group_settings(chat_id, flood_protection=int(not current))
    await cq.answer(f"محافظت سیل {'✅ فعال' if not current else '❌ غیرفعال'} شد.", show_alert=False)
    await cb_g_show(cq)


@router.callback_query(F.data.startswith("admin_g_forcesub_"))
async def cb_g_toggle_forcesub(cq: CallbackQuery):
    if cq.from_user.id not in ADMIN_IDS:
        return await cq.answer("❌ دسترسی نداری", show_alert=True)
    chat_id = int(cq.data.split("_")[-1])
    settings = await db.get_group_settings(chat_id)
    current = settings.get("force_sub_enabled", False) if settings else False
    await db.update_group_settings(chat_id, force_sub_enabled=int(not current))
    await cq.answer(f"عضویت اجباری {'✅ فعال' if not current else '❌ غیرفعال'} شد.", show_alert=False)
    await cb_g_show(cq)@router.callback_query(F.data.startswith("admin_g_ghistory_"))
async def cb_g_detail_history(cq: CallbackQuery):
    if cq.from_user.id not in ADMIN_IDS:
        return await cq.answer("❌ دسترسی نداری", show_alert=True)
    chat_id = int(cq.data.split("_")[-1])
    try:
        history = await db.get_chat_history(chat_id, limit=10)
    except:
        return await cq.message.edit_text("❌ خطا در دریافت تاریخچه.", reply_markup=_back_btn())
    if not history:
        return await cq.message.edit_text("❌ مکالماتی ثبت نشده.", reply_markup=_back_btn())
    text = f"📋 **آخرین مکالمات**\n\n"
    for i, h in enumerate(history, 1):
        role = "👤 کاربر" if h["role"] == "user" else "🤖 کتلت"
        text += f"{i}. {role}: {h['content'][:200]}\n\n"
    await cq.message.edit_text(text[:4000], reply_markup=_back_btn())


@router.callback_query(F.data.startswith("admin_g_gmsg_"))
async def cb_g_detail_gmsg(cq: CallbackQuery):
    if cq.from_user.id not in ADMIN_IDS:
        return await cq.answer("❌ دسترسی نداری", show_alert=True)
    chat_id = int(cq.data.split("_")[-1])
    await cq.message.edit_text(
        f"✉️ **متن پیام رو بفرست.**\n\n"
        f"پیام به آیدی زیر ارسال میشه:\n`{chat_id}`",
        reply_markup=_back_btn()
    )
    _pending[cq.from_user.id] = ("gmsg", chat_id)


@router.callback_query(F.data.startswith("admin_g_gleave_"))
async def cb_g_detail_gleave(cq: CallbackQuery):
    if cq.from_user.id not in ADMIN_IDS:
        return await cq.answer("❌ دسترسی نداری", show_alert=True)
    chat_id = int(cq.data.split("_")[-1])
    try:
        await cq.message.bot.leave_chat(chat_id)
        await db.remove_group(chat_id)
        await cq.answer("✅ خارج شدم.", show_alert=True)
    except Exception as e:
        return await cq.answer(f"❌ خطا: {e}", show_alert=True)
    await cb_g_ask(cq)


# ─── ارسال پیام ───

@router.callback_query(F.data == "admin_gmsg")
async def cb_gmsg_ask(cq: CallbackQuery):
    if cq.from_user.id not in ADMIN_IDS:
        return await cq.answer("❌ دسترسی نداری", show_alert=True)
    groups = await db.get_all_groups()
    if not groups:
        return await cq.message.edit_text("❌ هیچ گروهی نیست.", reply_markup=_back_btn())
    await cq.message.edit_text("✉️ **به کدوم گروه پیام بدم؟**", reply_markup=await _group_list_kb("admin_gmsg_sel"))


@router.callback_query(F.data.startswith("admin_gmsg_sel_"))
async def cb_gmsg_text(cq: CallbackQuery):
    if cq.from_user.id not in ADMIN_IDS:
        return await cq.answer("❌ دسترسی نداری", show_alert=True)
    chat_id = int(cq.data.split("_")[-1])
    await cq.message.edit_text(
        f"✉️ **متن پیام رو بفرست.**\n\n"
        f"به آیدی زیر ارسال میشه:\n`{chat_id}`",
        reply_markup=_back_btn()
    )
    _pending[cq.from_user.id] = ("gmsg", chat_id)


# ─── تاریخچه ───

@router.callback_query(F.data == "admin_ghistory")
async def cb_ghistory_ask(cq: CallbackQuery):
    if cq.from_user.id not in ADMIN_IDS:
        return await cq.answer("❌ دسترسی نداری", show_alert=True)
    groups = await db.get_all_groups()
    if not groups:
        return await cq.message.edit_text("❌ هیچ گروهی نیست.", reply_markup=_back_btn())
    await cq.message.edit_text("📋 **تاریخچه کدوم گروه؟**", reply_markup=await _group_list_kb("admin_ghistory_sel"))


@router.callback_query(F.data.startswith("admin_ghistory_sel_"))
async def cb_ghistory_show(cq: CallbackQuery):
    if cq.from_user.id not in ADMIN_IDS:
        return await cq.answer("❌ دسترسی نداری", show_alert=True)
    chat_id = int(cq.data.split("_")[-1])
    try:
        history = await db.get_chat_history(chat_id, limit=10)
    except:
        return await cq.message.edit_text("❌ خطا در دریافت تاریخچه.", reply_markup=_back_btn())
    if not history:
        return await cq.message.edit_text("❌ مکالماتی ثبت نشده.", reply_markup=_back_btn())
    text = f"📋 **آخرین مکالمات**\n\n"
    for i, h in enumerate(history, 1):
        role = "👤 کاربر" if h["role"] == "user" else "🤖 کتلت"
        text += f"{i}. {role}: {h['content'][:200]}\n\n"
    await cq.message.edit_text(text[:4000], reply_markup=_back_btn())


# ─── وضعیت AI ───

@router.callback_query(F.data == "admin_gtoggle")
async def cb_gtoggle_ask(cq: CallbackQuery):
    if cq.from_user.id not in ADMIN_IDS:
        return await cq.answer("❌ دسترسی نداری", show_alert=True)
    groups = await db.get_all_groups()
    if not groups:
        return await cq.message.edit_text("❌ هیچ گروهی نیست.", reply_markup=_back_btn())
    await cq.message.edit_text("🔄 **AI کدوم گروه رو تغییر بدم؟**", reply_markup=await _group_list_kb("admin_gtoggle_sel"))


@router.callback_query(F.data.startswith("admin_gtoggle_sel_"))
async def cb_gtoggle_do(cq: CallbackQuery):
    if cq.from_user.id not in ADMIN_IDS:
        return await cq.answer("❌ دسترسی نداری", show_alert=True)
    chat_id = int(cq.data.split("_")[-1])
    persona = await db.get_persona(chat_id)
    if persona:
        new_status = not persona["enabled"]
        await db.toggle_persona(chat_id, new_status)
        status = "✅ فعال" if new_status else "❌ غیرفعال"
    else:
        await db.set_persona(chat_id, "کُتلت", "تو یک ربات هوشمند هستی.")
        status = "✅ فعال"
    await cq.answer(f"AI {status} شد.", show_alert=False)
    await cb_gtoggle_ask(cq)


# ─── خروج از گروه ───

@router.callback_query(F.data == "admin_gleave")
async def cb_gleave_ask(cq: CallbackQuery):
    if cq.from_user.id not in ADMIN_IDS:
        return await cq.answer("❌ دسترسی نداری", show_alert=True)
    groups = await db.get_all_groups()
    if not groups:
        return await cq.message.edit_text("❌ هیچ گروهی نیست.", reply_markup=_back_btn())
    await cq.message.edit_text("🚪 **از کدوم گروه خارج بشم؟**", reply_markup=await _group_list_kb("admin_gleave_sel"))


@router.callback_query(F.data.startswith("admin_gleave_sel_"))
async def cb_gleave_do(cq: CallbackQuery):
    if cq.from_user.id not in ADMIN_IDS:
        return await cq.answer("❌ دسترسی نداری", show_alert=True)
    chat_id = int(cq.data.split("_")[-1])
    try:
        await cq.message.bot.leave_chat(chat_id)
        await db.remove_group(chat_id)
        await cq.answer("✅ خارج شدم.", show_alert=True)
    except Exception as e:
        return await cq.answer(f"❌ خطا: {e}", show_alert=True)
    await cb_gleave_ask(cq)


# ─── صفحه‌بندی ───

@router.callback_query(F.data.startswith("admin_page|"))
async def cb_page(cq: CallbackQuery):
    if cq.from_user.id not in ADMIN_IDS:
        return await cq.answer("❌ دسترسی نداری", show_alert=True)
    _, action, page_str = cq.data.split("|")
    page = int(page_str)
    await cq.message.edit_text("📌 **کدوم گروه؟**", reply_markup=await _group_list_kb(action, page))


# ─── دریافت متن از کاربر ───

_pending: dict = {}


@router.message(F.text, F.chat.type == "private")
async def pending_handler(message: Message):
    uid = message.from_user.id
    if uid not in _pending:
        return
    if uid not in ADMIN_IDS:
        return
    action, chat_id = _pending.pop(uid)
    if action == "gmsg":
        text = message.text.strip()
        try:
            await message.bot.send_message(chat_id, text)
            await message.answer("✅ **پیام ارسال شد.**", reply_markup=_back_btn())
        except Exception as e:
            await message.answer(f"❌ خطا: {e}")
