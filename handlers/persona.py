from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from database import db

router = Router()


@router.message(Command("setname"))
async def set_persona_name(message: Message):
    await message.reply("اسم ربات قابل تغییر نیست. اسمش کتلت است.")


@router.message(Command("setprompt"))
async def set_persona_prompt(message: Message):
    chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status not in ("creator", "administrator"):
        return await message.reply("فقط ادمین‌ها می‌تونن تنظیم کنن.")

    args = message.text.replace("/setprompt", "").strip()
    if not args:
        return await message.reply(
            "لطفاً پرامپت هوش مصنوعی رو بنویسید.\n"
            "مثال:\n"
            "/setprompt تو یک ربات شوخ طبع هستی. همیشه با لحن خنده دار جواب بده.\n\n"
            "با این دستور می‌تونید شخصیت هوش مصنوعی رو کامل تغییر بدید."
        )

    persona = await db.get_persona(message.chat.id)
    await db.set_persona(message.chat.id, "کتلت", args)

    await message.reply("پرامپت هوش مصنوعی بروزرسانی شد!")


@router.message(Command("toggleai"))
async def toggle_ai(message: Message):
    chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status not in ("creator", "administrator"):
        return await message.reply("فقط ادمین‌ها می‌تونن تنظیم کنن.")

    persona = await db.get_persona(message.chat.id)
    if persona:
        new_status = not persona["enabled"]
        await db.toggle_persona(message.chat.id, new_status)
        status = "فعال" if new_status else "غیرفعال"
        await message.reply(f"هوش مصنوعی {status} شد.")
    else:
        await db.set_persona(message.chat.id, "کتلت", "تو یک ربات هوشمند هستی.")
        await message.reply("هوش مصنوعی فعال شد.")


@router.message(Command("showprompt"))
async def show_persona(message: Message):
    persona = await db.get_persona(message.chat.id)
    if not persona:
        return await message.reply("هنوز شخصیتی تنظیم نشده.\nبا /setprompt می‌تونید تنظیم کنید.")

    status = "فعال" if persona["enabled"] else "غیرفعال"
    await message.reply(
        f"🤖 تنظیمات هوش مصنوعی:\n\n"
        f"📛 اسم: کتلت\n"
        f"📝 پرامپت:\n{persona['prompt']}\n\n"
        f"وضعیت: {status}"
    )


@router.message(Command("aiexamples"))
async def show_ai_examples(message: Message):
    await message.reply(
        "💡 مثال‌های پرامپت:\n\n"
        "🎯 ربات رسمی:\n"
        "تو یک دستیار رسمی هستی. با ادب و احترام جواب بده.\n\n"
        "😂 ربات شوخ:\n"
        "تو یک ربات شوخ طبع هستی. همیشه با لحن خنده دار جواب بده.\n\n"
        "🎮 ربات گیمر:\n"
        "تو یک گیمر حرفه‌ای هستی. در مورد بازی‌ها صحبت کن.\n\n"
        "📚 ربات دانشگاهی:\n"
        "تو یک استاد دانشگاه هستی. با توضیحات دقیق جواب بده.\n\n"
        "❤️ ربات عاشقانه:\n"
        "تو یک ربات عاشقانه هستی. با لحن عاشقانه جواب بده.\n\n"
        "با /setprompt شخصیت دلخواه خودتون رو بسازید!"
    )
