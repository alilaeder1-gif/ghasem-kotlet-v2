from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from database import db
from config import ADMIN_IDS

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.message(Command("admin"), F.chat.type == "private")
async def admin_menu(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "🔐 پنل مدیریت بات\n\n"
        "📊 /stats - آمار کلی بات\n"
        "👥 /groups - لیست گروه‌ها\n"
        "👤 /users - لیست کاربران\n"
        "💬 /g <chat_id> - جزئیات گروه\n"
        "✉️ /gmsg <chat_id> <متن> - ارسال پیام به گروه\n"
        "📋 /ghistory <chat_id> - آخرین مکالمات گروه\n"
        "🔄 /gtoggle <chat_id> - فعال/غیرفعال AI گروه\n"
        "🚪 /gleave <chat_id> - خروج از گروه\n"
        "📢 /broadcast <متن> - ارسال به همه گروه‌ها"
    )


@router.message(Command("stats"), F.chat.type == "private")
async def bot_stats(message: Message):
    if not is_admin(message.from_user.id):
        return
    try:
        groups = await db.get_all_groups()
        users_data = await db.get_all_users()
        group_count = len(groups)
        user_count = len(users_data)
        await message.answer(
            f"📊 آمار کلی بات:\n\n"
            f"👥 گروه‌ها: {group_count}\n"
            f"👤 کاربران: {user_count}"
        )
    except Exception as e:
        await message.answer(f"خطا: {e}")


@router.message(Command("groups"), F.chat.type == "private")
async def list_groups(message: Message):
    if not is_admin(message.from_user.id):
        return
    groups = await db.get_all_groups()
    if not groups:
        return await message.answer("هیچ گروهی نیست.")
    text = f"📋 گروه‌ها ({len(groups)}):\n\n"
    for i, g in enumerate(groups, 1):
        text += f"{i}. {g['title']}\n   👥 {g['members']} | 🆔 {g['chat_id']}\n\n"
    await message.answer(text[:4000])


@router.message(Command("users"), F.chat.type == "private")
async def list_users(message: Message):
    if not is_admin(message.from_user.id):
        return
    users = await db.get_all_users()
    if not users:
        return await message.answer("هیچ کاربری نیست.")
    text = f"👤 کاربران ({len(users)}):\n\n"
    for u in users[:30]:
        name = u["full_name"] or u["username"] or f"کاربر {u['user_id']}"
        text += f"• {name} | 🆔 <code>{u['user_id']}</code> | 🏘 {u['groups']} گروه\n"
    await message.answer(text[:4000])


@router.message(Command("g"), F.chat.type == "private")
async def group_detail(message: Message):
    if not is_admin(message.from_user.id):
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


@router.message(Command("gmsg"), F.chat.type == "private")
async def group_send(message: Message):
    if not is_admin(message.from_user.id):
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


@router.message(Command("ghistory"), F.chat.type == "private")
async def group_history(message: Message):
    if not is_admin(message.from_user.id):
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


@router.message(Command("gtoggle"), F.chat.type == "private")
async def group_toggle(message: Message):
    if not is_admin(message.from_user.id):
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


@router.message(Command("gleave"), F.chat.type == "private")
async def group_leave(message: Message):
    if not is_admin(message.from_user.id):
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


@router.message(Command("broadcast"), F.chat.type == "private")
async def cmd_broadcast(message: Message):
    if not is_admin(message.from_user.id):
        return
    text = message.text.replace("/broadcast", "").strip()
    if not text:
        return await message.answer("متن پیام رو بنویس. مثال: /broadcast سلام به همه")
    groups = await db.get_all_groups()
    if not groups:
        return await message.answer("هیچ گروهی نیست.")
    success = 0
    failed = 0
    for g in groups:
        try:
            await message.bot.send_message(g["chat_id"], text)
            success += 1
        except:
            failed += 1
    await message.answer(f"✅ ارسال: {success}\n❌ ناموفق: {failed}")
