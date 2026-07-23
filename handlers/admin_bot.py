from aiogram import Router, F
from aiogram.types import Message
from database import db
from config import ADMIN_IDS

router = Router()


@router.message(F.text == "/ghasemkotlet")
async def admin_menu(message: Message):
    if message.chat.type != "private":
        return
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer(
        "🔐 پنل مدیریت بات\n\n"
        "👥 /groups - لیست گروه‌ها\n"
        "👤 /users - لیست کاربران\n"
        "💬 /g [chat_id] - جزئیات گروه\n"
        "✉️ /gmsg [chat_id] [متن] - ارسال پیام به گروه\n"
        "📋 /ghistory [chat_id] - آخرین مکالمات گروه\n"
        "🔄 /gtoggle [chat_id] - فعال/غیرفعال AI گروه\n"
        "🚪 /gleave [chat_id] - خروج از گروه"
    )


@router.message(F.text == "/groups")
async def list_groups(message: Message):
    if message.chat.type != "private":
        return
    if message.from_user.id not in ADMIN_IDS:
        return
    groups = await db.get_all_groups()
    if not groups:
        return await message.answer("هیچ گروهی نیست.")
    text = f"📋 گروه‌ها ({len(groups)}):\n\n"
    for i, g in enumerate(groups, 1):
        text += f"{i}. {g['title']}\n   👥 {g['members']} | 🆔 {g['chat_id']}\n\n"
    await message.answer(text[:4000])


@router.message(F.text == "/users")
async def list_users(message: Message):
    if message.chat.type != "private":
        return
    if message.from_user.id not in ADMIN_IDS:
        return
    users = await db.get_all_users()
    if not users:
        return await message.answer("هیچ کاربری نیست.")
    text = f"👤 کاربران ({len(users)}):\n\n"
    for u in users[:30]:
        name = u["full_name"] or u["username"] or f"کاربر {u['user_id']}"
        text += f"• {name} | 🆔 <code>{u['user_id']}</code> | 🏘 {u['groups']} گروه\n"
    await message.answer(text[:4000])


@router.message(F.text.startswith("/g ") | (F.text == "/g"))
async def group_detail(message: Message):
    if message.chat.type != "private":
        return
    if message.from_user.id not in ADMIN_IDS:
        return
    args = message.text.replace("/g", "").strip()
    if not args:
        return await message.answer("آیدی گروه رو بگو. مثال: /g -1001234567890")
    try:
        chat_id = int(args.split()[0])
    except:
        return await message.answer("آیدی نامعتبر.")
    groups = await db.get_all_groups()
    g = next((x for x in groups if x["chat_id"] == chat_id), None)
    if not g:
        return await message.answer("این گروه تو پایگاه داده نیست.")
    settings = await db.get_group_settings(chat_id)
    ai_status = "فعال" if not settings or settings.get("ai_chat_enabled", True) else "غیرفعال"
    await message.answer(
        f"📌 {g['title']}\n\n"
        f"🆔 <code>{g['chat_id']}</code>\n"
        f"👥 اعضا: {g['members']}\n"
        f"🤖 AI: {ai_status}\n\n"
        f"دستورات:\n"
        f"/gtoggle {chat_id} - تغییر وضعیت AI\n"
        f"/ghistory {chat_id} - تاریخچه\n"
        f"/gmsg {chat_id} <متن> - ارسال پیام\n"
        f"/gleave {chat_id} - خروج"
    )


@router.message(F.text.startswith("/gmsg "))
async def group_send(message: Message):
    if message.chat.type != "private":
        return
    if message.from_user.id not in ADMIN_IDS:
        return
    parts = message.text.replace("/gmsg", "").strip().split(None, 1)
    if len(parts) < 2:
        return await message.answer("مثال: /gmsg -1001234567890 سلام به همه")
    try:
        chat_id = int(parts[0])
    except:
        return await message.answer("آیدی نامعتبر.")
    text = parts[1]
    try:
        await message.bot.send_message(chat_id, text)
        await message.answer("✅ ارسال شد.")
    except Exception as e:
        await message.answer(f"❌ خطا: {e}")


@router.message(F.text.startswith("/ghistory "))
async def group_history(message: Message):
    if message.chat.type != "private":
        return
    if message.from_user.id not in ADMIN_IDS:
        return
    args = message.text.replace("/ghistory", "").strip()
    if not args:
        return await message.answer("آیدی گروه رو بگو. مثال: /ghistory -1001234567890")
    try:
        chat_id = int(args.split()[0])
    except:
        return await message.answer("آیدی نامعتبر.")
    try:
        history = await db.get_chat_history(chat_id, limit=10)
    except:
        return await message.answer("مکالماتی نیست.")
    if not history:
        return await message.answer("مکالماتی ثبت نشده.")
    text = f"📋 آخرین مکالمات:\n\n"
    for i, h in enumerate(history, 1):
        role = "👤 کاربر" if h["role"] == "user" else "🤖 کتلت"
        text += f"{i}. {role}: {h['content'][:200]}\n\n"
    await message.answer(text[:4000])


@router.message(F.text.startswith("/gtoggle "))
async def group_toggle(message: Message):
    if message.chat.type != "private":
        return
    if message.from_user.id not in ADMIN_IDS:
        return
    args = message.text.replace("/gtoggle", "").strip()
    if not args:
        return await message.answer("آیدی گروه رو بگو. مثال: /gtoggle -1001234567890")
    try:
        chat_id = int(args.split()[0])
    except:
        return await message.answer("آیدی نامعتبر.")
    persona = await db.get_persona(chat_id)
    if persona:
        new_status = not persona["enabled"]
        await db.toggle_persona(chat_id, new_status)
        status = "فعال" if new_status else "غیرفعال"
        await message.answer(f"AI گروه {status} شد.")
    else:
        await db.set_persona(chat_id, "کُتلت", "تو یک ربات هوشمند هستی.")
        await message.answer("AI گروه فعال شد.")


@router.message(F.text.startswith("/gleave "))
async def group_leave(message: Message):
    if message.chat.type != "private":
        return
    if message.from_user.id not in ADMIN_IDS:
        return
    args = message.text.replace("/gleave", "").strip()
    if not args:
        return await message.answer("آیدی گروه رو بگو. مثال: /gleave -1001234567890")
    try:
        chat_id = int(args.split()[0])
    except:
        return await message.answer("آیدی نامعتبر.")
    try:
        await message.bot.leave_chat(chat_id)
        await db.remove_group(chat_id)
        await message.answer("✅ خارج شدم.")
    except Exception as e:
        await message.answer(f"❌ خطا: {e}")
