from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command
from database import db
from config import ADMIN_IDS
from handlers.key_pool import all_pools_status, gemini_pool, groq_pool, openrouter_pool
from handlers.ai_gateway import daily_usage, health_score

router = Router()
_pending: dict = {}

# ─── helpers ───

def _back(cb: str = "apanel_back") -> InlineKeyboardMarkup:
    return InlineKeyboardBuilder().button(text="🔙 برگشت", callback_data=cb).as_markup()

def _check(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# ─── main menu ───

_ADMIN_MENU = [
    ("🤖 وضعیت AI", "apanel_ai"),
    ("👥 مدیریت کاربران", "apanel_users"),
    ("📊 آمار مصرف", "apanel_stats"),
    ("📢 ارسال همگانی", "apanel_broadcast"),
    ("⚙️ تنظیمات زنده", "apanel_settings"),
    ("🧹 پاکسازی حافظه", "apanel_memory"),
]

@router.message(Command("panel"))
async def cmd_panel(message: Message):
    if not _check(message.from_user.id):
        return
    if message.chat.type != "private":
        return
    b = InlineKeyboardBuilder()
    for label, cb in _ADMIN_MENU:
        b.button(text=label, callback_data=cb)
    b.adjust(2)
    await message.answer("🔐 **پنل مدیریت پیشرفته**", reply_markup=b.as_markup())

@router.callback_query(F.data == "apanel_back")
async def cb_back(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    b = InlineKeyboardBuilder()
    for label, cb in _ADMIN_MENU:
        b.button(text=label, callback_data=cb)
    b.adjust(2)
    await cq.message.edit_text("🔐 **پنل مدیریت پیشرفته**", reply_markup=b.as_markup())

# ─── 1. AI Dashboard ───

@router.callback_query(F.data == "apanel_ai")
async def cb_ai_status(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    pools = all_pools_status()
    lines = ["🤖 **وضعیت سرویس‌های AI**\n"]
    for name, info in pools.items():
        emoji = "🟢" if info["healthy"] == info["total"] and info["total"] > 0 else ("🟡" if info["healthy"] > 0 else "🔴")
        lines.append(f"{emoji} **{name}**: {info['healthy']}/{info['total']} سالم")
        if info["cooldown"] > 0:
            lines.append(f"   ⏳ {info['cooldown']} در cooldown")
        if info["dead"] > 0:
            lines.append(f"   💀 {info['dead']} مرده")
        lines.append(f"   📞 {info['total_calls']} تماس")
    lines.append("")
    for provider in ["gemini", "groq", "openrouter"]:
        for model, limit in [("gemini-2.0-flash", None), ("llama-3.3-70b-versatile", None),
                              ("llama-3.1-8b-instant", None), ("deepseek/deepseek-chat", None),
                              ("qwen/qwen-2.5-coder-32b-instruct", None)]:
            h = health_score.get(model)
            if h > 0:
                bar = "🟢" if h >= 60 else ("🟡" if h >= 30 else "🔴")
                lines.append(f"  {bar} {model}: %{h:.0f}")
    await cq.message.edit_text("\n".join(lines)[:4000], reply_markup=_back())

# ─── 2. User Management ───

@router.callback_query(F.data == "apanel_users")
async def cb_users_menu(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    total = 0
    try:
        users = await db.get_all_users()
        total = len(users)
    except: pass
    b = InlineKeyboardBuilder()
    b.button(text="🔍 جستجوی کاربر", callback_data="apanel_users_search")
    b.button(text="📊 آمار کاربران", callback_data="apanel_users_stats")
    b.button(text="🔙 برگشت", callback_data="apanel_back")
    b.adjust(2)
    await cq.message.edit_text(
        f"👥 **مدیریت کاربران**\n\nکل: `{total}` کاربر",
        reply_markup=b.as_markup()
    )

@router.callback_query(F.data == "apanel_users_search")
async def cb_users_search_ask(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    _pending[cq.from_user.id] = "users_search"
    await cq.message.edit_text(
        "🔍 **آیدی کاربر رو بفرست** (مثال: `123456789`)",
        reply_markup=_back()
    )

@router.callback_query(F.data == "apanel_users_stats")
async def cb_users_stats(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    try:
        users = await db.get_all_users()
        total = len(users)
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        active_today = sum(1 for u in users if (u.get("last_seen") or "")[:10] == today)
        text = f"📊 **آمار کاربران**\n\n"
        text += f"👥 کل: `{total}`\n"
        text += f"🟢 فعال امروز: `{active_today}`\n"
    except Exception as e:
        text = f"❌ خطا: {e}"
    await cq.message.edit_text(text, reply_markup=_back())

# ─── 3. Usage Stats ───

@router.callback_query(F.data == "apanel_stats")
async def cb_stats(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    pools = all_pools_status()
    total_tokens = 0
    total_calls = 0
    for name, info in pools.items():
        total_calls += info["total_calls"]
    lines = ["📊 **آمار مصرف**\n"]
    from handlers.ai_gateway import daily_usage
    for provider in ["gemini", "groq", "openrouter"]:
        pool = {"gemini": gemini_pool, "groq": groq_pool, "openrouter": openrouter_pool}.get(provider)
        if not pool: continue
        for k in pool.keys:
            u = daily_usage.get_usage(k.key)
            if u["calls"] > 0:
                lines.append(f"• {provider} ...{k.key[-4:]}: {u['calls']} calls / {u['tokens']} tokens")
    lines.append(f"\n📞 کل تماس‌ها: `{total_calls}`")
    await cq.message.edit_text("\n".join(lines)[:4000], reply_markup=_back())

# ─── 4. Broadcast ───

@router.callback_query(F.data == "apanel_broadcast")
async def cb_broadcast_ask(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    _pending[cq.from_user.id] = "broadcast"
    await cq.message.edit_text(
        "📢 **متن پیام همگانی رو بفرست**\n\n"
        "به همه گروه‌هایی که بات عضو هست ارسال میشه.",
        reply_markup=_back()
    )

# ─── 5. Live Settings ───

_SETTINGS_OPTIONS = [
    ("max_tokens", "256", "🔢 حداکثر توکن"),
    ("temperature", "1.0", "🌡 درجه خلاقیت"),
    ("context_limit", "12000", "📏 حداکثر ورودی"),
]

@router.callback_query(F.data == "apanel_settings")
async def cb_settings(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    from config import settings as cfg
    lines = ["⚙️ **تنظیمات زنده**\n\n"]
    b = InlineKeyboardBuilder()
    for key, default, label in _SETTINGS_OPTIONS:
        val = getattr(cfg, key, default)
        lines.append(f"{label}: `{val}`")
        b.button(text=f"✏️ {label}", callback_data=f"apanel_set_{key}")
    b.button(text="🔙 برگشت", callback_data="apanel_back")
    b.adjust(2)
    await cq.message.edit_text("\n".join(lines), reply_markup=b.as_markup())

@router.callback_query(F.data.startswith("apanel_set_"))
async def cb_set_ask(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    key = cq.data.split("_", 2)[-1]
    _pending[cq.from_user.id] = ("set", key)
    await cq.message.edit_text(
        f"✏️ **مقدار جدید برای `{key}` رو بفرست**",
        reply_markup=_back()
    )

# ─── 6. Memory Manager ───

@router.callback_query(F.data == "apanel_memory")
async def cb_memory(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    b = InlineKeyboardBuilder()
    b.button(text="🧹 پاکسازی حافظه یه کاربر", callback_data="apanel_mem_clear")
    b.button(text="📊 وضعیت حافظه", callback_data="apanel_mem_stats")
    b.button(text="🔙 برگشت", callback_data="apanel_back")
    b.adjust(2)
    await cq.message.edit_text("🧹 **مدیریت حافظه**", reply_markup=b.as_markup())

@router.callback_query(F.data == "apanel_mem_clear")
async def cb_mem_clear_ask(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    _pending[cq.from_user.id] = "mem_clear"
    await cq.message.edit_text(
        "🔍 **آیدی کاربر رو بفرست** تا حافظه AIش پاک بشه.",
        reply_markup=_back()
    )

@router.callback_query(F.data == "apanel_mem_stats")
async def cb_mem_stats(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    try:
        from database import db
        total = await db.get_memory_count() if hasattr(db, "get_memory_count") else 0
    except: total = "?"
    text = f"📊 **وضعیت حافظه**\n\nتعداد حافظه‌های ذخیره شده: `{total}`\n\n"
    text += "برای پاکسازی حافظه یک کاربر:\n`🧹 پاکسازی حافظه` از منو"
    await cq.message.edit_text(text, reply_markup=_back("apanel_memory"))

# ─── pending message handler ───

@router.message(F.text, F.chat.type == "private")
async def pending_handler(message: Message):
    uid = message.from_user.id
    if uid not in _pending: return
    if not _check(uid): return
    action = _pending.pop(uid)
    text = message.text.strip()

    if action == "users_search":
        try:
            uid_search = int(text)
        except ValueError:
            return await message.answer("❌ آیدی کاربر باید عدد باشه.", reply_markup=_back())
        try:
            users = await db.get_all_users()
            user = next((u for u in users if u.get("user_id") == uid_search), None)
            if not user:
                return await message.answer("❌ کاربر پیدا نشد.", reply_markup=_back())
            mem = await db.get_user_memory(uid_search, 0) if uid_search else ""
            b = InlineKeyboardBuilder()
            b.button(text="🚫 بلاک/رفع بلاک", callback_data=f"apanel_block_{uid_search}")
            b.button(text="🧹 پاک کردن حافظه", callback_data=f"apanel_memdo_{uid_search}")
            b.button(text="🔙 برگشت", callback_data="apanel_users")
            b.adjust(2)
            await message.answer(
                f"👤 **کاربر پیدا شد**\n\n"
                f"🆔 `{user.get('user_id')}`\n"
                f"👤 {user.get('full_name', 'نامشخص')}\n"
                f"🧠 حافظه: {len(mem or '')} کاراکتر",
                reply_markup=b.as_markup()
            )
        except Exception as e:
            await message.answer(f"❌ خطا: {e}", reply_markup=_back())

    elif action == "broadcast":
        try:
            groups = await db.get_all_groups()
            sent = 0
            failed = 0
            for g in groups:
                try:
                    await message.bot.send_message(g["chat_id"], text)
                    sent += 1
                except:
                    failed += 1
            await message.answer(f"📢 **ارسال شد**\n\n✅ موفق: {sent}\n❌ ناموفق: {failed}", reply_markup=_back())
        except Exception as e:
            await message.answer(f"❌ خطا: {e}", reply_markup=_back())

    elif isinstance(action, tuple) and action[0] == "set":
        key = action[1]
        try:
            from config import settings as cfg
            val = int(text) if text.isdigit() else float(text) if "." in text else text
            setattr(cfg, key, val)
            await message.answer(f"✅ `{key}` = `{val}` ذخیره شد.", reply_markup=_back("apanel_settings"))
        except Exception as e:
            await message.answer(f"❌ خطا: {e}", reply_markup=_back())

    elif action == "mem_clear":
        try:
            uid_clear = int(text)
            try:
                await db.save_user_memory(uid_clear, 0, "")
                await message.answer(f"✅ حافظه کاربر `{uid_clear}` پاک شد.", reply_markup=_back("apanel_memory"))
            except Exception as e:
                await message.answer(f"❌ خطا: {e}", reply_markup=_back("apanel_memory"))
        except ValueError:
            await message.answer("❌ آیدی کاربر باید عدد باشه.", reply_markup=_back("apanel_memory"))

# ─── block / unblock ───

@router.callback_query(F.data.startswith("apanel_block_"))
async def cb_block(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    uid = int(cq.data.split("_")[-1])
    try:
        users = await db.get_all_users()
        groups = [u["chat_id"] for u in users if u.get("user_id") == uid]
        if not groups:
            groups = [0]
        chat_id = groups[0]
        banned = await db.is_banned(chat_id, uid)
        if banned:
            await db.unban_user(chat_id, uid)
            await cq.answer("✅ رفع بلاک شد.", show_alert=True)
        else:
            await db.ban_user(chat_id, uid, "blocked by admin")
            await cq.answer("🚫 بلاک شد.", show_alert=True)
    except Exception as e:
        await cq.answer(f"❌ {e}", show_alert=True)

@router.callback_query(F.data.startswith("apanel_memdo_"))
async def cb_mem_clear_do(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    uid = int(cq.data.split("_")[-1])
    try:
        await db.save_user_memory(uid, 0, "")
        await cq.answer(f"✅ حافظه `{uid}` پاک شد.", show_alert=True)
    except Exception as e:
        await cq.answer(f"❌ {e}", show_alert=True)
