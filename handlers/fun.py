import asyncio
import random
import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, ChatPermissions
from aiogram.filters import Command
from database import db

logger = logging.getLogger(__name__)
router = Router()

games = {}
reminders = {}


@router.message(Command("tag", "all"))
async def tag_all(message: Message):
    chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status not in ("creator", "administrator"):
        return await message.reply("فقط ادمین‌ها می‌تونن منشن کنن.")

    args = message.text.split(None, 1)
    text = args[1] if len(args) > 1 else ""

    users = await db.get_group_users(message.chat.id)
    if not users:
        return await message.reply("هیچ کاربری پیدا نشد.")

    mentions = []
    for u in users[:30]:
        name = u["full_name"] or u["username"] or f"user{u['user_id']}"
        mentions.append(f"[{name}](tg://user?id={u['user_id']})")

    chunk_size = 5
    for i in range(0, len(mentions), chunk_size):
        chunk = mentions[i:i + chunk_size]
        msg = " ".join(chunk)
        if text:
            msg = f"{text}\n\n{msg}"
        await message.reply(msg)
        await asyncio.sleep(1)


@router.message(Command("summary"))
async def group_summary(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        return

    users = await db.get_group_users(message.chat.id)
    if not users:
        return await message.reply("هنوز آماری ثبت نشده.")

    total = sum(u["messages"] for u in users)
    top = sorted(users, key=lambda x: x["messages"], reverse=True)[:10]

    text = f"📊 خلاصه گروه\n\n"
    text += f"مجموع پیام‌ها: {total}\n\n"
    text += f"🏆 پرحرف‌ترین‌ها:\n"
    for i, u in enumerate(top, 1):
        name = u["full_name"] or u["username"] or f"کاربر {u['user_id']}"
        text += f"{i}. {name} — {u['messages']} پیام\n"

    await message.reply(text)


@router.message(Command("game"))
async def start_game(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        return

    chat_id = message.chat.id
    if chat_id in games:
        return await message.reply("قبلاً یه بازی شروع شده!")

    words = ["کتلت", "تلگرام", "ایران", "پیتزا", "فوتبال", "کامپیوتر", "موزیک", "برنامه"]
    word = random.choice(words)
    hint = "_ " * len(word)

    games[chat_id] = {"word": word, "guessed": set(), "hint": hint.strip(), "tries": 0}

    await message.reply(
        f"🎮 بازی حدس کلمه!\n\n"
        f"کلمه: {hint}\n\n"
        f"با /guess <حرف> حدس بزن. مثلاً: /guess ک\n"
        f"با /guessword <کلمه> می‌تونی کل کلمه رو حدس بزنی."
    )


@router.message(Command("guess"))
async def guess_letter(message: Message):
    chat_id = message.chat.id
    if chat_id not in games:
        return await message.reply("بازی شروع نشده. /game بزن.")

    args = message.text.replace("/guess", "").strip()
    if not args:
        return await message.reply("یک حرف بزن. مثال: /guess ک")

    letter = args[0]
    game = games[chat_id]
    word = game["word"]
    game["tries"] += 1

    if letter in word:
        game["guessed"].add(letter)
        display = "".join(c if c in game["guessed"] else "_ " for c in word)

        if "_" not in display:
            del games[chat_id]
            return await message.reply(f"🎉 آفرین! کلمه «{word}» بود!\nتعداد حدس‌ها: {game['tries']}")
        else:
            await message.reply(f"✅ درسته! کلمه: {display}")
    else:
        await message.reply(f"❌ غلط! حرف «{letter}» تو کلمه نیست.")


@router.message(Command("guessword"))
async def guess_word(message: Message):
    chat_id = message.chat.id
    if chat_id not in games:
        return await message.reply("بازی شروع نشده. /game بزن.")

    args = message.text.replace("/guessword", "").strip()
    if not args:
        return await message.reply("کلمه رو بگو. مثال: /guessword کتلت")

    game = games[chat_id]
    word = game["word"]
    game["tries"] += 1

    if args == word:
        del games[chat_id]
        await message.reply(f"🎉 آفرین! کلمه «{word}» بود!\nتعداد حدس‌ها: {game['tries']}")
    else:
        await message.reply(f"❌ غلط! کلمه «{args}» درست نیست.")


@router.message(Command("stopgame"))
async def stop_game(message: Message):
    chat_id = message.chat.id
    if chat_id in games:
        word = games[chat_id]["word"]
        del games[chat_id]
        await message.reply(f"🛑 بازی تموم شد. کلمه «{word}» بود.")
    else:
        await message.reply("بازی در جریان نیست.")


async def reminder_worker():
    while True:
        now = datetime.now()
        to_remove = []
        for rid, r in reminders.items():
            if r["time"] <= now:
                try:
                    await r["bot"].send_message(
                        chat_id=r["chat_id"],
                        text=f"⏰ یادآوری برای {r['user_name']}:\n{r['message']}"
                    )
                except:
                    pass
                to_remove.append(rid)
        for rid in to_remove:
            del reminders[rid]
        await asyncio.sleep(10)


@router.message(Command("remind"))
async def set_reminder(message: Message):
    text = message.text.replace("/remind", "").strip()
    if not text:
        return await message.reply(
            "مثال:\n"
            "/remind 5 سلام به همه بگم\n"
            "/remind 10 برم ناهار بخورم\n\n"
            "عدد به معنی دقیقه هست."
        )

    parts = text.split(None, 1)
    if not parts[0].isdigit():
        return await message.reply("اول یه عدد بگو (دقیقه). مثال: /remind 5 پیام من")
    minutes = int(parts[0])
    msg = parts[1] if len(parts) > 1 else "یادآوری!"

    remind_time = datetime.now() + timedelta(minutes=minutes)
    rid = len(reminders) + 1
    reminders[rid] = {
        "chat_id": message.chat.id,
        "user_name": message.from_user.first_name or "رفیق",
        "message": msg,
        "time": remind_time,
        "bot": message.bot
    }

    await message.reply(f"✅ یادآوری برای {minutes} دقیقه بعد تنظیم شد!\nپیام: {msg}")


@router.message(Command("reminders"))
async def list_reminders(message: Message):
    active = [r for r in reminders.values() if r["chat_id"] == message.chat.id]
    if not active:
        return await message.reply("یادآوری فعالی وجود نداره.")

    text = "⏰ یادآوری‌های فعال:\n\n"
    for rid, r in reminders.items():
        if r["chat_id"] == message.chat.id:
            remaining = (r["time"] - datetime.now()).seconds // 60
            text += f"#{rid}: «{r['message']}» - {remaining} دقیقه دیگه\n"
    await message.reply(text)
