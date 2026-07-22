from aiogram import Router, F, Bot
from aiogram.types import Message, ChatMemberUpdated, Chat
from aiogram.filters import ChatMemberUpdatedFilter, Command
from database import db

router = Router()


@router.message(F.chat.type.in_({"group", "supergroup"}))
async def track_group(message: Message):
    await db.add_group(message.chat.id, message.chat.title or "بدون نام", message.chat.username or "")
    try:
        member_count = await message.bot.get_chat_member_count(message.chat.id)
        await db.update_group_member_count(message.chat.id, member_count)
    except:
        pass


@router.message(Command("sync"))
async def sync_groups(message: Message):
    if message.from_user.id not in [int(x) for x in __import__('os').getenv('ADMIN_IDS', '').split(',') if x.strip()]:
        return await message.reply("فقط ادمین اصلی می‌تونه این کار رو بکنه.")

    await track_group(message)
    return await message.reply("✅ گروه همگام‌سازی شد. حالا توی پنل می‌بینی.")


@router.chat_member(ChatMemberUpdatedFilter(member_status_changed="left -> joined"))
async def on_bot_added(event: ChatMemberUpdated):
    chat = event.chat
    member_count = 0
    try:
        member_count = await event.bot.get_chat_member_count(chat.id)
    except Exception:
        pass

    username = chat.username or ""
    await db.add_group(chat.id, chat.title, username, member_count)

    try:
        await event.answer(
            f"سلام! 👋\nمن کُتلت هستم.\n\n"
            f"از اضافه کردنم به گروه «{chat.title}» ممنونم!\n\n"
            f"برای شروع /start رو بزنید.\n"
            f"برای راهنما /help رو بزنید."
        )
    except Exception:
        pass


@router.chat_member(ChatMemberUpdatedFilter(member_status_changed="joined -> left"))
async def on_bot_removed(event: ChatMemberUpdated):
    await db.remove_group(event.chat.id)


@router.message(Command("mygroups"))
async def my_groups(message: Message):
    if message.from_user.id not in [int(x) for x in __import__('os').getenv('ADMIN_IDS', '').split(',') if x.strip()]:
        return await message.reply("فقط ادمین اصلی می‌تونه این دستور رو بزنه.")

    groups = await db.get_all_groups()
    if not groups:
        return await message.reply("ربات هیچ گروهی نیست.")

    text = f"📋 گروه‌های ربات ({len(groups)} گروه):\n\n"
    for i, g in enumerate(groups, 1):
        text += f"{i}. {g['title']}\n   👥 {g['members']} عضو\n   🆔 {g['chat_id']}\n\n"
    await message.reply(text)


@router.message(Command("broadcast"))
async def broadcast(message: Message):
    if message.from_user.id not in [int(x) for x in __import__('os').getenv('ADMIN_IDS', '').split(',') if x.strip()]:
        return await message.reply("فقط ادمین اصلی می‌تونه این دستور رو بزنه.")

    text = message.text.replace("/broadcast", "").strip()
    if not text:
        return await message.reply("لطفاً متن پیام رو بنویسید.\nمثال: /broadcast سلام به همه!")

    groups = await db.get_all_groups()
    if not groups:
        return await message.reply("هیچ گروهی پیدا نشد.")

    success = 0
    failed = 0
    for g in groups:
        try:
            await message.bot.send_message(g["chat_id"], text)
            success += 1
        except Exception:
            failed += 1

    await message.reply(f"✅ ارسال شد: {success}\n❌ ناموفق: {failed}")


@router.message(Command("groupstats"))
async def group_stats(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        return await message.reply("این دستور فقط در گروه کار می‌کنه.")

    users = await db.get_group_users(message.chat.id)
    total_messages = sum(u["messages"] for u in users)

    await message.reply(
        f"📊 آمار گروه «{message.chat.title}»:\n\n"
        f"👥 تعداد کاربران: {len(users)}\n"
        f"💬 کل پیام‌ها: {total_messages}\n"
        f"🏆 فعال‌ترین کاربر:\n"
        f"   {users[0]['full_name'] if users else 'ندارد'} ({users[0]['messages'] if users else 0} پیام)"
    )


@router.message(Command("userinfo"))
async def user_info(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        return await message.reply("این دستور فقط در گروه کار می‌کنه.")

    target_user = message.from_user
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user

    user_data = await db.get_user(message.chat.id, target_user.id)
    if not user_data:
        return await message.reply("اطلاعات این کاربر پیدا نشد.")

    await message.reply(
        f"👤 اطلاعات کاربر:\n\n"
        f"📛 نام: {user_data['full_name']}\n"
        f"🆔 آیدی: {user_data['user_id']}\n"
        f"💬 پیام‌ها: {user_data['message_count']}\n"
        f"👑 ادمین: {'بله' if user_data['is_admin'] else 'خیر'}\n"
        f"📅 اولین حضور: {user_data['first_seen']}\n"
        f"🕐 آخرین حضور: {user_data['last_seen']}"
    )
