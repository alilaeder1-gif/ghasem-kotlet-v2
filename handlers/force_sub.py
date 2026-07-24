from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command
from database import db

router = Router()


def _force_sub_kb(channel: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📢 عضویت در کانال", url=f"https://t.me/{channel}")
    b.button(text="✅ تایید عضویت", callback_data=f"forcesub_verify_{channel}")
    b.adjust(1)
    return b.as_markup()


async def is_subscribed(bot, user_id: int, channel: str) -> bool:
    try:
        member = await bot.get_chat_member(f"@{channel}", user_id)
        return member.status not in ("left", "kicked")
    except Exception:
        return False


async def check_and_warn(bot, message: Message, channel: str) -> bool:
    if await is_subscribed(bot, message.from_user.id, channel):
        return True
    try:
        await message.delete()
    except Exception:
        pass
    try:
        await message.answer(
            f"⛔ **{message.from_user.full_name}**\n\n"
            f"🔒 برای ارسال پیام در گروه، ابتدا عضو کانال زیر شوید:\n"
            f"📢 @{channel}\n\n"
            f"پس از عضویت، دکمه ✅ تایید عضویت را بزنید.",
            reply_markup=_force_sub_kb(channel),
            disable_web_page_preview=True
        )
    except Exception:
        pass
    return False


@router.message(Command("forcesub"))
async def set_force_sub(message: Message):
    chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status not in ("creator", "administrator"):
        return await message.reply("فقط ادمین‌ها می‌تونن تنظیم کنن.")

    args = message.text.replace("/forcesub", "").strip().split()
    if len(args) < 1:
        return await message.reply(
            "برای تنظیم عضویت اجباری:\n\n"
            "/forcesub @channel_username - فعال کردن\n"
            "/forcesub off - غیرفعال کردن\n\n"
            "کاربران باید در کانال عضو باشن تا بتونن پیام بفرسن."
        )

    if args[0].lower() == "off":
        await db.update_group_settings(message.chat.id, force_sub_enabled=0, force_sub_channel="")
        return await message.reply("❌ عضویت اجباری غیرفعال شد.")

    channel = args[0].lstrip("@")
    await db.update_group_settings(message.chat.id, force_sub_enabled=1, force_sub_channel=channel)
    await message.reply(
        f"✅ عضویت اجباری فعال شد!\n"
        f"📢 کانال: @{channel}\n\n"
        f"کاربرانی که عضو کانال نباشن نمی‌تونن پیام بفرسن."
    )


@router.callback_query(F.data.startswith("forcesub_verify_"))
async def verify_subscription(cq: CallbackQuery):
    channel = cq.data.split("forcesub_verify_", 1)[1]
    user_id = cq.from_user.id

    if await is_subscribed(cq.bot, user_id, channel):
        try:
            await cq.message.edit_text(
                f"✅ {cq.from_user.full_name} عضویت شما تأیید شد!\n"
                f"اکنون می‌توانید پیام بفرستید.",
                reply_markup=None
            )
            await cq.answer("✅ عضویت تأیید شد!", show_alert=False)
        except Exception:
            pass
    else:
        try:
            await cq.answer(
                "❌ شما هنوز عضو کانال نشدید!\n"
                "لطفاً ابتدا عضو شوید.",
                show_alert=True
            )
        except Exception:
            pass
