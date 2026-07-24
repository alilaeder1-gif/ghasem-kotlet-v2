import time
import hashlib
import logging
from datetime import datetime, timezone
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command
from database import db
from config import ADMIN_IDS
from handlers.key_pool import all_pools_status, gemini_pool, groq_pool, openrouter_pool, huggingface_pool, KeyPool
from handlers.ai_gateway import daily_usage, health_score

router = Router()
_pending: dict = {}
logger = logging.getLogger(__name__)

# ─── PIN Authentication ───

_PIN_ATTEMPTS: dict[int, int] = {}
_PIN_PENDING: set[int] = set()
_PIN_TIMEOUT = 86400
_PIN_MAX_ATTEMPTS = 5
_PIN_COOLDOWN = 300

async def _get_pin_hash() -> str | None:
    try: return await db.get_setting("admin_pin_hash") or None
    except: return None

async def _set_pin_hash(pin: str):
    h = hashlib.sha256(pin.encode()).hexdigest()
    await db.set_setting("admin_pin_hash", h)

async def _clear_pin():
    await db.set_setting("admin_pin_hash", "")

async def _check_session(uid: int) -> bool:
    exp_str = await db.get_setting(f"admin_session_{uid}")
    if exp_str:
        try:
            return time.time() < float(exp_str)
        except: pass
    return False

async def _save_session(uid: int):
    exp = str(time.time() + _PIN_TIMEOUT)
    await db.set_setting(f"admin_session_{uid}", exp)

async def _clear_session(uid: int = None):
    if uid:
        await db.set_setting(f"admin_session_{uid}", "")

async def _ensure_pin(message: Message) -> bool:
    uid = message.from_user.id
    if not _check(uid): return False
    if await _check_session(uid): return True
    pin_hash = await _get_pin_hash()
    if not pin_hash:
        _pending[uid] = "set_pin"
        await message.answer(
            "🔐 **تنظیم PIN مدیریت**\n\n"
            "اولین باره که وارد میشی. یه **PIN چهار تا شش رقمی** "
            "برای دسترسی به پنل انتخاب کن.\n\n"
            "✏️ فقط عدد بفرست (مثلاً `1234`)",
        )
        return False
    _PIN_PENDING.add(uid)
    remaining = _PIN_MAX_ATTEMPTS - _PIN_ATTEMPTS.get(uid, 0)
    if remaining <= 0:
        await message.answer(f"⏳ **زیاد تلاش کردی!** {_PIN_COOLDOWN // 60} دقیقه صبر کن.")
        return False
    await message.answer(f"🔐 **PIN مدیریت رو وارد کن** ({remaining} تلاش باقی مونده)")
    return False

async def _show_dashboard(message: Message):
    await message.answer("🏠 **داشبورد مدیریت کتلت**\nاز منوی زیر گزینه مورد نظر رو انتخاب کن.", reply_markup=_main_kb())

# ─── In-memory stats ───

class _Stats:
    def __init__(self):
        self.requests_today = 0
        self.response_times: list[float] = []
        self.last_errors: dict[str, str] = {}
        self.error_log: list[dict] = []
        self._day = datetime.now(timezone.utc).date()

    def record_request(self, latency: float = 0):
        today = datetime.now(timezone.utc).date()
        if today != self._day:
            self.requests_today = 0
            self.response_times = []
            self._day = today
        self.requests_today += 1
        if latency > 0:
            self.response_times.append(latency)
            if len(self.response_times) > 1000:
                self.response_times = self.response_times[-500:]

    def record_error(self, provider: str, model: str, error: str):
        now = datetime.now().strftime("%H:%M")
        self.last_errors[f"{provider}/{model}"] = error[:100]
        self.error_log.append({"time": now, "provider": provider, "model": model, "error": error[:80]})
        if len(self.error_log) > 200:
            self.error_log = self.error_log[-100:]

    def avg_response(self) -> float:
        if not self.response_times:
            return 0.0
        recent = self.response_times[-50:]
        return round(sum(recent) / len(recent), 1)

    def get_logs(self, n: int = 20) -> list[dict]:
        return self.error_log[-n:]

_stats = _Stats()

# ─── helpers ───

def _back(cb: str = "apanel_back") -> InlineKeyboardMarkup:
    return InlineKeyboardBuilder().button(text="🔙 برگشت", callback_data=cb).as_markup()

def _check(user_id: int) -> bool:
    return user_id in ADMIN_IDS

_MAIN_MENU = [
    ("🏠 داشبورد", "apanel_dashboard"),
    ("🤖 وضعیت AI", "apanel_ai"),
    ("👑 مدیریت API Keys", "apanel_keys"),
    ("👥 مدیریت کاربران", "apanel_users"),
    ("📊 آمار مصرف", "apanel_stats"),
    ("💬 مدیریت پرامپت", "apanel_prompts"),
    ("📝 لاگ خطاها", "apanel_logs"),
    ("📢 ارسال همگانی", "apanel_broadcast"),
    ("⚙️ تنظیمات زنده", "apanel_settings"),
    ("🧹 مدیریت حافظه", "apanel_memory"),
    ("🔐 تغییر PIN", "apanel_pin"),
    ("📚 پاسخ‌های آماده", "apanel_offline"),
    ("❓ سوالات بی‌جواب", "apanel_unanswered"),
    ("🔀 Feature Flags", "apanel_feature_flags"),
]

def _main_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for label, cb in _MAIN_MENU:
        b.button(text=label, callback_data=cb)
    b.adjust(2)
    return b.as_markup()

@router.message(Command("panel"))
async def cmd_panel(message: Message):
    if message.chat.type != "private": return
    if not _check(message.from_user.id): return
    try:
        if not await _ensure_pin(message): return
        await _show_dashboard(message)
    except Exception as e:
        logger.error(f"cmd_panel error: {e}")
        await message.answer(f"❌ خطا: {str(e)[:100]}")

@router.message(Command("setpin"))
async def cmd_setpin(message: Message):
    if message.chat.type != "private": return
    if not _check(message.from_user.id): return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        _pending[message.from_user.id] = "set_pin"
        return await message.answer("✏️ **PIN جدید (۴ تا ۶ رقمی) رو بفرست**\nمثل: `/setpin 1234`")
    pin = args[1].strip()
    if not pin.isdigit() or len(pin) < 4 or len(pin) > 6:
        return await message.answer("❌ PIN باید ۴ تا ۶ رقمی باشه.")
    await _set_pin_hash(pin)
    await _save_session(message.from_user.id)
    await message.answer("✅ **PIN تنظیم شد.**\nاز این به بعد با این PIN وارد پنل میشی.")

@router.message(Command("resetpin"))
async def cmd_resetpin(message: Message):
    if message.chat.type != "private": return
    if not _check(message.from_user.id): return
    await _clear_pin()
    await _clear_session(message.from_user.id)
    await message.answer(
        "✅ **PIN پاک شد.**\n\n"
        "دفعه بعد که وارد پنل بشی، دوباره ازت می‌خوام یه PIN جدید انتخاب کنی."
    )

@router.callback_query(F.data == "apanel_back")
async def cb_back(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    await cq.message.edit_text("🔐 **پنل مدیریت پیشرفته**", reply_markup=_main_kb())

# ═══════════════════════════════════════════
# 1. DASHBOARD
# ═══════════════════════════════════════════

@router.callback_query(F.data == "apanel_dashboard")
async def cb_dashboard(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    try:
        users = await db.get_all_users()
        total_users = len(users)
        today = datetime.now().strftime("%Y-%m-%d")
        online = sum(1 for u in users if u.get("last_seen", "").startswith(today))
    except: total_users = online = "?"
    pools = all_pools_status()
    lines = [
        "🏠 **داشبورد سیستم**\n",
        f"👥 کاربران: `{total_users}` | 🔥 آنلاین امروز: `{online}`",
        f"🤖 درخواست امروز: `{_stats.requests_today}`",
        f"⚡ میانگین پاسخ: `{_stats.avg_response()}s`\n",
    ]
    service_map = {
        "gemini": ("🟢", "🟡", "🔴"),
        "groq": ("🟢", "🟡", "🔴"),
        "openrouter": ("🟢", "🟡", "🔴"),
        "redis": ("🟢", None, "🔴"),
        "database": ("🟢", None, "🔴"),
    }
    for name, info in pools.items():
        emoji = "🟢" if info["total"] > 0 and info["healthy"] == info["total"] else ("🟡" if info["healthy"] > 0 else "🔴")
        lines.append(f"{emoji} **{name}**: {info['healthy']}/{info['total']} سالم")

    # Service status (Redis, DB)
    try:
        import cache
        redis_ok = cache.cache.enabled
    except: redis_ok = False
    lines.append(f"{'🟢' if redis_ok else '🔴'} **Redis**: {'متصل' if redis_ok else 'قطع'}")
    lines.append(f"🟢 **Database**: متصل")
    lines.append(f"🟢 **Railway**: فعال")

    await cq.message.edit_text("\n".join(lines)[:4000], reply_markup=_back())

# ═══════════════════════════════════════════
# 2. AI DASHBOARD (Enhanced)
# ═══════════════════════════════════════════

@router.callback_query(F.data == "apanel_ai")
async def cb_ai_status(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    pools = all_pools_status()
    lines = ["🤖 **وضعیت سرویس‌های AI**\n"]

    # Provider health from scheduler
    try:
        from handlers.key_scheduler import get_provider_status
        prov_status = get_provider_status()
        if prov_status:
            lines.append("**🔄 وضعیت لحظه‌ای Providerها:**")
            icons = {"healthy": "🟢", "ratelimit": "🟡", "dead": "🔴", "no_keys": "⚪", "unknown": "🔵", "timeout": "🟠"}
            for prov, st in sorted(prov_status.items()):
                icon = icons.get(st, "❓")
                lines.append(f"  {icon} {prov}: {st}")
            lines.append("")
    except ImportError:
        pass

    for name, info in pools.items():
        emoji = "🟢" if info["total"] > 0 and info["healthy"] == info["total"] else ("🟡" if info["healthy"] > 0 else "🔴")
        lines.append(f"{emoji} **{name}**: {info['healthy']}/{info['total']} سالم")
        if info["cooldown"] > 0: lines.append(f"   ⏳ {info['cooldown']} cooldown")
        if info["dead"] > 0: lines.append(f"   💀 {info['dead']} مرده")
        lines.append(f"   📞 {info['total_calls']} تماس")
        err = _stats.last_errors.get(name)
        if err: lines.append(f"   ❌ آخرین خطا: `{err[:60]}`")
    lines.append("")
    lines.append("**Health Score هر مدل:**")
    for provider in ["gemini", "groq", "openrouter"]:
        for model_entry in [("gemini-2.0-flash",), ("llama-3.3-70b-versatile",), ("llama-3.1-8b-instant",),
                            ("deepseek/deepseek-chat",), ("qwen/qwen-2.5-coder-32b-instruct",)]:
            model = model_entry[0]
            h = health_score.get(model)
            if h > 0:
                bar = "🟢" if h >= 60 else ("🟡" if h >= 30 else "🔴")
                lines.append(f"  {bar} {model}: %{h:.0f}")
    await cq.message.edit_text("\n".join(lines)[:4000], reply_markup=_back())

# ═══════════════════════════════════════════
# 3. API KEY MANAGER
# ═══════════════════════════════════════════

_OVERLAY_KEYS: dict[str, list[str]] = {}  # runtime key overrides

@router.callback_query(F.data == "apanel_keys")
async def cb_keys_menu(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    pools = {"gemini": gemini_pool, "groq": groq_pool, "openrouter": openrouter_pool, "huggingface": huggingface_pool}
    lines = ["👑 **مدیریت API Keys**\n"]
    b = InlineKeyboardBuilder()
    for name, pool in pools.items():
        status = pool.status()
        healthy = status["healthy"]
        cooldown = status["cooldown"]
        dead = status["dead"]
        emoji = "🟢" if healthy == status["total"] else ("🟡" if healthy > 0 else "🔴")
        lines.append(f"{emoji} **{name}**: 🟢 {healthy} سالم | ⏳ {cooldown} cooldown | 💀 {dead} مرده")
        b.button(text=f"👁 {name}", callback_data=f"apanel_key_detail_{name}")
        b.button(text=f"➕ {name}", callback_data=f"apanel_key_add_{name}")
        if dead > 0:
            b.button(text=f"♻️ {name}", callback_data=f"apanel_key_revive_{name}")
    b.button(text="🔙 برگشت", callback_data="apanel_back")
    b.adjust(3)
    await cq.message.edit_text("\n".join(lines)[:4000], reply_markup=b.as_markup())

@router.callback_query(F.data.startswith("apanel_key_detail_"))
async def cb_key_detail(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    provider = cq.data.split("_")[-1]
    pool = {"gemini": gemini_pool, "groq": groq_pool, "openrouter": openrouter_pool, "huggingface": huggingface_pool}.get(provider)
    if not pool: return
    lines = [f"👑 **{provider}** - {len(pool.keys)} کلید\n"]
    b = InlineKeyboardBuilder()
    for idx, k in enumerate(pool.keys):
        s = "🟢" if k.is_available() else ("⏳" if k.cooldown_until and time.time() < k.cooldown_until else "🔴")
        health_bar = "🟢" if k.health >= 60 else ("🟡" if k.health >= 30 else "🔴")
        cooldown_info = ""
        if k.cooldown_until and time.time() < k.cooldown_until:
            remaining = int((k.cooldown_until - time.time()) / 60)
            cooldown_info = f" ⏳{remaining}m"
        lines.append(f"{s} `...{k.key[-8:]}` {health_bar}%{k.health:.0f} 📞{k.total_calls}{cooldown_info}")
        b.button(text=f"❌ {idx+1}", callback_data=f"apanel_key_del_{provider}_{idx}")
        b.button(text=f"🔄 {idx+1}", callback_data=f"apanel_key_test_{provider}_{idx}")
        b.button(text=f"🔌 {idx+1}", callback_data=f"apanel_key_toggle_{provider}_{idx}")
    b.button(text=f"➕ Add", callback_data=f"apanel_key_add_{provider}")
    b.button(text="🔙 برگشت", callback_data="apanel_keys")
    b.adjust(3)
    await cq.message.edit_text("\n".join(lines)[:4000], reply_markup=b.as_markup())

@router.callback_query(F.data.startswith("apanel_key_add_"))
async def cb_key_add_ask(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    provider = cq.data.split("_")[-1]
    _pending[cq.from_user.id] = ("add_key", provider)
    var_name = {"gemini": "GEMINI_API_KEY", "groq": "GROQ_API_KEY", "openrouter": "OPENROUTER_API_KEY", "huggingface": "HF_API_KEY"}.get(provider, provider.upper() + "_API_KEY")
    await cq.message.edit_text(
        f"✏️ **کلید جدید برای `{provider}`**\n\n"
        f"فرمت: `{var_name}=your_key`\n"
        f"فقط مقدار key رو بفرست (مثلاً `AIzaSy...`)\n"
        f"یا با متغیر: `{var_name}=...`",
        reply_markup=_back()
    )

@router.callback_query(F.data.startswith("apanel_key_del_"))
async def cb_key_del(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    _, _, provider, idx = cq.data.split("_", 3)
    idx = int(idx)
    pool = {"gemini": gemini_pool, "groq": groq_pool, "openrouter": openrouter_pool, "huggingface": huggingface_pool}.get(provider)
    if pool and 0 <= idx < len(pool.keys):
        ks = pool.keys[idx]
        if ks.db_id:
            try: await db.remove_api_key(ks.db_id)
            except: pass
        pool.remove_key(idx)
        logger.info(f"Admin removed key ...{ks.key[-4:]} from {provider}")
        await cq.answer("✅ کلید از دیتابیس حذف شد.", show_alert=True)
    else:
        await cq.answer("❌ خطا", show_alert=True)
    await cb_keys_menu(cq)

@router.callback_query(F.data.startswith("apanel_key_toggle_"))
async def cb_key_toggle(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    _, _, provider, idx = cq.data.split("_", 3)
    idx = int(idx)
    pool = {"gemini": gemini_pool, "groq": groq_pool, "openrouter": openrouter_pool, "huggingface": huggingface_pool}.get(provider)
    if pool and 0 <= idx < len(pool.keys):
        k = pool.keys[idx]
        k.healthy = not k.healthy
        if not k.healthy:
            k.cooldown_until = time.time() + 86400
        else:
            k.cooldown_until = 0
            k.failures = 0
        if k.db_id:
            try:
                import asyncio
                asyncio.ensure_future(pool._sync_to_db(k))
            except: pass
        await cq.answer(f"{'🔴 غیرفعال' if not k.healthy else '🟢 فعال'} شد.", show_alert=True)
    await cb_keys_menu(cq)

@router.callback_query(F.data.startswith("apanel_key_revive_"))
async def cb_key_revive(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    provider = cq.data.split("_")[-1]
    pool = {"gemini": gemini_pool, "groq": groq_pool, "openrouter": openrouter_pool, "huggingface": huggingface_pool}.get(provider)
    if not pool: return
    revived = 0
    for k in pool.keys:
        if not k.healthy:
            k.healthy = True
            k.failures = 0
            k.cooldown_until = 0
            if k.db_id:
                try:
                    import asyncio
                    asyncio.ensure_future(pool._sync_to_db(k))
                except: pass
            revived += 1
    await cq.answer(f"♻️ {revived} کلید revived شد.", show_alert=True)
    await cb_keys_menu(cq)

@router.callback_query(F.data.startswith("apanel_key_test_"))
async def cb_key_test(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    parts = cq.data.split("_")
    provider = parts[3]
    idx = int(parts[4])
    pool = {"gemini": gemini_pool, "groq": groq_pool, "openrouter": openrouter_pool, "huggingface": huggingface_pool}.get(provider)
    if not pool or idx < 0 or idx >= len(pool.keys): return
    k = pool.keys[idx]
    await cq.answer("⏳ تست کلید...", show_alert=False)
    try:
        import requests as _r
        headers = {"Authorization": f"Bearer {k.key}", "Content-Type": "application/json"}
        data = {"model": "gemini-2.0-flash" if provider == "gemini" else ("llama-3.3-70b-versatile" if provider == "groq" else "deepseek/deepseek-chat"), "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5}
        if provider == "gemini":
            from google import genai as _genai
            _client = _genai.Client(api_key=k.key)
            resp = _client.models.generate_content(model="gemini-2.0-flash", contents="ping")
            ok = bool(resp.text)
        else:
            base = "https://api.groq.com/openai/v1" if provider == "groq" else "https://openrouter.ai/api/v1"
            r = _r.post(f"{base}/chat/completions", headers=headers, json=data, timeout=10)
            ok = r.status_code == 200
        if ok:
            k.healthy = True
            k.failures = 0
            await cq.answer("✅ کلید سالم است.", show_alert=True)
        else:
            await cq.answer("❌ کلید کار نمی‌کند.", show_alert=True)
    except Exception as e:
        await cq.answer(f"❌ خطا: {str(e)[:50]}", show_alert=True)
    if k.db_id:
        try:
            import asyncio
            asyncio.ensure_future(pool._sync_to_db(k))
        except: pass
    await cb_key_detail(cq)

# ═══════════════════════════════════════════
# 4. USER MANAGER (Enhanced)
# ═══════════════════════════════════════════

@router.callback_query(F.data == "apanel_users")
async def cb_users_menu(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    try:
        users = await db.get_all_users()
        total = len(users)
    except: total = "?"
    b = InlineKeyboardBuilder()
    b.button(text="🔍 جستجوی کاربر", callback_data="apanel_users_search")
    b.button(text="📊 آمار", callback_data="apanel_users_stats")
    b.button(text="🔙 برگشت", callback_data="apanel_back")
    b.adjust(2)
    await cq.message.edit_text(f"👥 **مدیریت کاربران**\n\nکل: `{total}` کاربر", reply_markup=b.as_markup())

@router.callback_query(F.data == "apanel_users_search")
async def cb_users_search_ask(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    _pending[cq.from_user.id] = "users_search"
    await cq.message.edit_text("🔍 **آیدی کاربر رو بفرست**", reply_markup=_back())

@router.callback_query(F.data == "apanel_users_stats")
async def cb_users_stats(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    try:
        users = await db.get_all_users()
        total = len(users)
        today = datetime.now().strftime("%Y-%m-%d")
        active_today = sum(1 for u in users if (u.get("last_seen") or "")[:10] == today)
        await cq.message.edit_text(
            f"📊 **آمار کاربران**\n\n👥 کل: `{total}`\n🟢 فعال امروز: `{active_today}`",
            reply_markup=_back()
        )
    except Exception as e:
        await cq.message.edit_text(f"❌ خطا: {e}", reply_markup=_back())

# ═══════════════════════════════════════════
# 5. USAGE STATS (Enhanced)
# ═══════════════════════════════════════════

@router.callback_query(F.data == "apanel_stats")
async def cb_stats(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    today_users = await db.count_today_users()
    online_users = await db.count_online_users(30)
    ai_reqs = await db.count_ai_requests_today()
    offline_reqs = await db.count_offline_responses_today()
    prov_stats = await db.get_provider_stats()
    groups = await db.get_group_count()
    all_users = await db.get_all_users()
    total_users = len(all_users)

    # Messages today (from ai_log + qa_memory)
    msg_today = 0
    try:
        async with db.db.execute("SELECT COUNT(*) as cnt FROM qa_memory WHERE date(created_at) = date('now')") as c:
            row = await c.fetchone()
            msg_today = row["cnt"] if row else 0
    except: pass

    # Failover count (cached in _stats)
    failover_count = sum(1 for l in _stats.error_log if l.get("error", "")) if _stats.error_log else 0

    # Most used model
    most_used = "—"
    try:
        async with db.db.execute(
            "SELECT provider, COUNT(*) as cnt FROM ai_log GROUP BY provider ORDER BY cnt DESC LIMIT 1"
        ) as c:
            row = await c.fetchone()
            if row: most_used = f"{row['provider']} ({row['cnt']})"
    except: pass

    # Health status
    health_line = ""
    try:
        from handlers.health_monitor import get_health_summary
        hs = get_health_summary()
        if hs:
            icons = {"healthy": "🟢", "ratelimit": "🟡", "unauthorized": "🔴", "no_keys": "⚪", "disabled": "⚪"}
            health_line = "  ".join(f"{icons.get(v.split(':')[0], '❓')}{k}" for k, v in hs.items())
    except: pass

    # Queue stats
    queue_line = ""
    try:
        from handlers.ai_queue import ai_queue
        qs = ai_queue.stats()
        if qs["processed"] > 0:
            queue_line = f"📦 صف: {qs['queued']} منتظر | {qs['active']} فعال | {qs['avg_wait_sec']}s انتظار"
    except: pass

    lines = ["📊 **داشبورد آمار**\n"]

    # Section 1: Users
    lines.append("**👥 کاربران**")
    lines.append(f"کل: `{total_users}` | امروز: `{today_users}` | آنلاین: `{online_users}`")
    lines.append(f"گروه‌ها: `{groups}` | پیام‌های امروز: `{msg_today}`\n")

    # Section 2: AI
    lines.append("**🤖 هوش مصنوعی**")
    total_reqs = ai_reqs + offline_reqs
    success_pct = round(ai_reqs / total_reqs * 100, 1) if total_reqs else 0
    fail_pct = round(100 - success_pct, 1) if total_reqs else 0
    lines.append(f"🟢 AI: `{ai_reqs}` | 📚 Offline: `{offline_reqs}` | ✅ موفقیت: `{success_pct}%`")
    lines.append(f"🔄 Failover: `{failover_count}` | 🏆 پرمصرف: `{most_used}`")
    if queue_line:
        lines.append(queue_line)

    # Section 3: Provider breakdown — 24h / 7d / 30d
    lines.append(f"\n**📡 موفقیت Provider:**")
    lines.append(f"{'Provider':<14} {'24h':<8} {'7d':<8} {'30d':<8}")
    try:
        range_24h = await db.get_provider_stats_range(1)
        range_7d = await db.get_provider_stats_range(7)
        range_30d = await db.get_provider_stats_range(30)
        stats_map_24h = {r["provider"]: r for r in range_24h}
        stats_map_7d = {r["provider"]: r for r in range_7d}
        stats_map_30d = {r["provider"]: r for r in range_30d}
        all_provs = set(list(stats_map_24h.keys()) + list(stats_map_7d.keys()) + list(stats_map_30d.keys()))
        for prov in sorted(all_provs):
            def _pct(d: dict) -> str:
                total = d.get("success", 0) + d.get("failure", 0)
                if not total: return "—"
                p = d["success"] / total * 100
                return f"{p:.0f}%"
            p24 = _pct(stats_map_24h.get(prov, {}))
            p7 = _pct(stats_map_7d.get(prov, {}))
            p30 = _pct(stats_map_30d.get(prov, {}))
            lines.append(f"{prov:<14} {p24:<8} {p7:<8} {p30:<8}")
    except: pass

    # Section 4: Token usage
    total_tokens = 0
    provider_breakdown = []
    for provider in ["gemini", "groq", "openrouter"]:
        pool = {"gemini": gemini_pool, "groq": groq_pool, "openrouter": openrouter_pool, "huggingface": huggingface_pool}.get(provider)
        if not pool: continue
        prov_toks = 0
        for k in pool.keys:
            u = daily_usage.get_usage(k.key)
            if u and u["calls"] > 0:
                prov_toks += u["tokens"]
                total_tokens += u["tokens"]
        if prov_toks > 0:
            provider_breakdown.append(f"{provider}: {prov_toks:,}")
    lines.append(f"\n**💰 مصرف و هزینه**")
    lines.append(f"💎 توکن امروز: `{total_tokens:,}`")
    if provider_breakdown:
        lines.append(f"   " + " | ".join(provider_breakdown))
    cost_est = round(total_tokens * 0.000002, 4)
    lines.append(f"💵 هزینه تخمینی: `${cost_est}`")

    # Section 5: Performance
    lines.append(f"\n**⚡ عملکرد**")
    lines.append(f"میانگین پاسخ: `{_stats.avg_response()}s`")
    lines.append(f"آخرین خطا: `{_stats.last_error or '—'}`")

    # Section 6: Live health
    if health_line:
        lines.append(f"\n**🩺 وضعیت سیستمی**")
        lines.append(health_line)

    await cq.message.edit_text("\n".join(lines)[:4000], reply_markup=_back())

# ═══════════════════════════════════════════
# 6. PROMPT MANAGER
# ═══════════════════════════════════════════

@router.callback_query(F.data == "apanel_prompts")
async def cb_prompts(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    b = InlineKeyboardBuilder()
    for label, key, pname in [
        ("✏️ System Prompt", "system", "system_prompt"),
        ("✏️ Lite Prompt", "lite", "lite_prompt"),
        ("✏️ Memory Prompt", "memory", "memory_prompt"),
    ]:
        b.button(text=label, callback_data=f"apanel_prompt_view_{key}")
    b.button(text="🔄 بازنشانی پیش‌فرض", callback_data="apanel_prompt_reset")
    b.button(text="🔙 برگشت", callback_data="apanel_back")
    b.adjust(1)
    current = "system"
    try: current = (await db.get_setting("current_prompt")) or "system"
    except: pass
    await cq.message.edit_text(
        f"💬 **مدیریت پرامپت‌ها**\n\nپرامپت فعال: `{current}`\n\n"
        "هر پرامپت رو می‌تونی ویرایش کنی بدون نیاز به Deploy.",
        reply_markup=b.as_markup()
    )

@router.callback_query(F.data.startswith("apanel_prompt_view_"))
async def cb_prompt_view(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    key = cq.data.split("_")[-1]
    try: text = await db.get_setting(f"custom_{key}_prompt")
    except: text = None
    if not text:
        text = "(پیش‌فرض فعال است)"
    b = InlineKeyboardBuilder()
    b.button(text="✏️ ویرایش", callback_data=f"apanel_prompt_edit_{key}")
    b.button(text="🔄 بازنشانی پیش‌فرض", callback_data=f"apanel_prompt_rst_{key}")
    b.button(text="🔙 برگشت", callback_data="apanel_prompts")
    b.adjust(2)
    await cq.message.edit_text(
        f"💬 **پرامپت `{key}`**\n\n"
        f"```\n{text[:1500]}\n```\n\n"
        f"({len(text)} کاراکتر)",
        reply_markup=b.as_markup()
    )

@router.callback_query(F.data.startswith("apanel_prompt_edit_"))
async def cb_prompt_edit_ask(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    key = cq.data.split("_")[-1]
    _pending[cq.from_user.id] = ("edit_prompt", key)
    await cq.message.edit_text(
        f"✏️ **متن جدید برای پرامپت `{key}` رو بفرست**\n\n"
        "همینطور که می‌خوای ذخیره بشه تایپ کن.",
        reply_markup=_back()
    )

@router.callback_query(F.data.startswith("apanel_prompt_rst_"))
async def cb_prompt_reset(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    key = cq.data.split("_")[-1]
    try:
        await db.set_setting(f"custom_{key}_prompt", "")
        await cq.answer(f"✅ پرامپت `{key}` به پیش‌فرض برگشت.", show_alert=True)
    except Exception as e:
        await cq.answer(f"❌ {e}", show_alert=True)
    await cb_prompts(cq)

# ═══════════════════════════════════════════
# 7. LOG VIEWER
# ═══════════════════════════════════════════

@router.callback_query(F.data == "apanel_logs")
async def cb_logs(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    b = InlineKeyboardBuilder()
    b.button(text="🔴 خطاها", callback_data="apanel_logs_errors")
    b.button(text="🤖 درخواست‌های AI", callback_data="apanel_logs_ai")
    b.button(text="🔙 برگشت", callback_data="apanel_back")
    b.adjust(2)
    await cq.message.edit_text("📝 **لاگ‌ها**\n\nکدوم لاگ رو می‌خوای ببینی؟", reply_markup=b.as_markup())

@router.callback_query(F.data == "apanel_logs_errors")
async def cb_logs_errors(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    logs = _stats.get_logs(30)
    if not logs:
        return await cq.message.edit_text("📝 **لاگ خطاها**\n\nهیچ خطایی ثبت نشده.", reply_markup=_back("apanel_logs"))
    lines = ["📝 **آخرین خطاها**\n"]
    for log in logs[-20:]:
        emoji = "🔴" if "fail" in log["error"].lower() or "4" in log["error"][:1] else "🟡"
        lines.append(f"{emoji} {log['time']} {log['provider']} {log['model'][:25]}")
        lines.append(f"   `{log['error'][:60]}`")
    await cq.message.edit_text("\n".join(lines)[:4000], reply_markup=_back("apanel_logs"))

@router.callback_query(F.data == "apanel_logs_ai")
async def cb_logs_ai(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    logs = await db.get_ai_logs(30)
    if not logs:
        return await cq.message.edit_text("📝 **لاگ AI**\n\nهیچ درخواستی ثبت نشده.", reply_markup=_back("apanel_logs"))
    lines = ["📝 **آخرین درخواست‌های AI**\n"]
    for log in logs[:20]:
        ts = log.get("created_at", "")[11:19] if log.get("created_at") else ""
        prov = log.get("provider", "") or "-"
        rtype = {"ai": "🤖", "offline": "📚", "cache": "⚡"}.get(log.get("response_type", ""), "❓")
        lat = log.get("latency", 0)
        q = log.get("question", "")[:30]
        lines.append(f"{rtype} {ts} [{prov}] {lat}s")
        lines.append(f"   `{q}`")
    await cq.message.edit_text("\n".join(lines)[:4000], reply_markup=_back("apanel_logs"))

# ═══════════════════════════════════════════
# 8. BROADCAST
# ═══════════════════════════════════════════

@router.callback_query(F.data == "apanel_broadcast")
async def cb_broadcast_ask(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    _pending[cq.from_user.id] = "broadcast"
    await cq.message.edit_text(
        "📢 **متن پیام همگانی رو بفرست**\n\n"
        "به همه گروه‌هایی که بات عضو هست ارسال میشه.",
        reply_markup=_back()
    )

# ═══════════════════════════════════════════
# 9. LIVE SETTINGS
# ═══════════════════════════════════════════

_LIVE_OPTS = [
    ("max_tokens", "256", "🔢 حداکثر توکن"),
    ("temperature", "1.0", "🌡 خلاقیت"),
    ("context_limit", "12000", "📏 حداکثر ورودی"),
]

@router.callback_query(F.data == "apanel_settings")
async def cb_settings(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    from config import settings as cfg
    lines = ["⚙️ **تنظیمات زنده**\n\n"]
    b = InlineKeyboardBuilder()
    for key, default, label in _LIVE_OPTS:
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

# ═══════════════════════════════════════════
# FEATURE FLAGS
# ═══════════════════════════════════════════

@router.callback_query(F.data == "apanel_feature_flags")
async def cb_feature_flags(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    from handlers.feature_flags import feature_flags
    b = InlineKeyboardBuilder()
    lines = ["🔀 **Feature Flags**\n\nهر قابلیت رو بدون Deploy روشن/خاموش کن.\n"]
    flags = {
        "AI Chat": "ai_chat", "Anti Spam": "anti_spam", "Anti Link": "anti_link",
        "Anti Flood": "anti_flood", "Broadcast": "broadcast", "Welcome": "welcome",
        "Health Monitor": "health_monitor", "AI Queue": "ai_queue", "Backup": "backup",
    }
    for label, key in flags.items():
        enabled = await feature_flags.is_enabled(key)
        icon = "✅" if enabled else "❌"
        lines.append(f"{icon} {label}")
        b.button(text=f"{'✅' if enabled else '❌'} {label}", callback_data=f"apanel_flag_{key}")
    b.button(text="🔙 برگشت", callback_data="apanel_back")
    b.adjust(1)
    await cq.message.edit_text("\n".join(lines)[:4000], reply_markup=b.as_markup())

@router.callback_query(F.data.startswith("apanel_flag_"))
async def cb_flag_toggle(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    flag = cq.data.split("_", 2)[-1]
    from handlers.feature_flags import feature_flags
    new_val = await feature_flags.toggle(flag)
    await cq.answer(f"{'✅' if new_val else '❌'} {flag}: {'ON' if new_val else 'OFF'}", show_alert=True)
    await cb_feature_flags(cq)
    await cq.message.edit_text(f"✏️ **مقدار جدید برای `{key}`**", reply_markup=_back())

# ═══════════════════════════════════════════
# 10. MEMORY MANAGER
# ═══════════════════════════════════════════

@router.callback_query(F.data == "apanel_memory")
async def cb_memory(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    b = InlineKeyboardBuilder()
    b.button(text="🧹 پاکسازی یه کاربر", callback_data="apanel_mem_clear_one")
    b.button(text="🗑 پاکسازی همه", callback_data="apanel_mem_clear_all")
    b.button(text="📊 وضعیت", callback_data="apanel_mem_stats")
    b.button(text="🔙 برگشت", callback_data="apanel_back")
    b.adjust(2)
    await cq.message.edit_text("🧹 **مدیریت حافظه**", reply_markup=b.as_markup())

@router.callback_query(F.data == "apanel_mem_clear_one")
async def cb_mem_clear_ask(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    _pending[cq.from_user.id] = "mem_clear"
    await cq.message.edit_text("🔍 **آیدی کاربر رو بفرست** برای پاک کردن حافظه.", reply_markup=_back())

@router.callback_query(F.data == "apanel_mem_clear_all")
async def cb_mem_clear_all(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    try:
        await db.db.execute("DELETE FROM user_memory")
        await db.db.commit()
        await cq.answer("✅ حافظه همه کاربران پاک شد.", show_alert=True)
    except Exception as e:
        await cq.answer(f"❌ {e}", show_alert=True)
    await cb_memory(cq)

@router.callback_query(F.data == "apanel_mem_stats")
async def cb_mem_stats(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    try:
        async with db.db.execute("SELECT COUNT(*) as cnt FROM user_memory") as cursor:
            row = await cursor.fetchone()
            total = row["cnt"] if row else 0
        async with db.db.execute("SELECT SUM(LENGTH(memory)) as total_bytes FROM user_memory") as cursor:
            row = await cursor.fetchone()
            bytes_total = row["total_bytes"] if row else 0
        await cq.message.edit_text(
            f"📊 **وضعیت حافظه**\n\n"
            f"📝 تعداد: `{total}`\n"
            f"💾 حجم: `{bytes_total // 1024}` KB",
            reply_markup=_back("apanel_memory"))
    except Exception as e:
        await cq.message.edit_text(f"❌ {e}", reply_markup=_back("apanel_memory"))

# ═══════════════════════════════════════════
# PIN MANAGEMENT
# ═══════════════════════════════════════════

@router.callback_query(F.data == "apanel_pin")
async def cb_pin_menu(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    b = InlineKeyboardBuilder()
    b.button(text="🔐 تغییر PIN", callback_data="apanel_pin_change")
    b.button(text="🗑 حذف PIN", callback_data="apanel_pin_remove")
    b.button(text="🔙 برگشت", callback_data="apanel_back")
    b.adjust(2)
    await cq.message.edit_text(
        "🔐 **مدیریت PIN**\n\n"
        "PIN یه رمز ۴ تا ۶ رقمی برای دسترسی به پنل مدیریته.\n"
        "تا ۲۴ ساعت توی حافظه می‌مونه (حتی بعد ری‌استارت).\n\n"
        "اگر PIN رو فراموش کردی:\n"
        "• از دستور `/resetpin` توی پیوی بات استفاده کن",
        reply_markup=b.as_markup()
    )

@router.callback_query(F.data == "apanel_pin_change")
async def cb_pin_change(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    _pending[cq.from_user.id] = "set_pin"
    await _clear_session(cq.from_user.id)
    await cq.message.edit_text("✏️ **PIN جدید (۴ تا ۶ رقمی) رو بفرست**", reply_markup=_back("apanel_pin"))

@router.callback_query(F.data == "apanel_pin_remove")
async def cb_pin_remove(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    await _clear_pin()
    await _clear_session(cq.from_user.id)
    await cq.answer("✅ PIN حذف شد. دیگه برای ورود PIN لازم نیست.", show_alert=True)
    await cb_pin_menu(cq)

# ═══════════════════════════════════════════
# OFFLINE ANSWERS MANAGER
# ═══════════════════════════════════════════

def _clear_kb_cache():
    try:
        from handlers.knowledge_engine import clear_cache
        clear_cache()
    except ImportError:
        pass
    try:
        from handlers.intent_engine import clear_cache as clear_intent_cache
        clear_intent_cache()
    except ImportError:
        pass

@router.callback_query(F.data == "apanel_offline")
async def cb_offline_menu(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    answers = await db.get_all_offline_answers()
    lines = ["📚 **پاسخ‌های آماده (Offline)**\n\n"]
    b = InlineKeyboardBuilder()
    for a in answers:
        intent = a["intent"]
        answer_preview = a["answer"][:30]
        lines.append(f"• `{intent}`: {answer_preview}...")
        b.button(text=f"✏️ {intent}", callback_data=f"apanel_off_edit_{a['id']}")
        b.button(text=f"❌ {intent}", callback_data=f"apanel_off_del_{a['id']}")
    lines.append(f"\n{len(answers)} پاسخ آماده")
    b.button(text="➕ جدید", callback_data="apanel_off_add")
    b.button(text="🔙 برگشت", callback_data="apanel_back")
    b.adjust(2)
    await cq.message.edit_text("\n".join(lines)[:4000], reply_markup=b.as_markup())

@router.callback_query(F.data == "apanel_off_add")
async def cb_off_add(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    _pending[cq.from_user.id] = "offline_new_intent"
    await cq.message.edit_text("✏️ **اسم intent رو بفرست** (مثلاً: greeting, farewell, price)\n\nاین دسته‌بندی پاسخه.", reply_markup=_back("apanel_offline"))

@router.callback_query(F.data.startswith("apanel_off_edit_"))
async def cb_off_edit(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    aid = int(cq.data.split("_")[-1])
    _pending[cq.from_user.id] = ("offline_edit", aid)
    await cq.message.edit_text("✏️ **متن جدید پاسخ رو بفرست**\n\nفرمت: intent | triggers | answer\nمثال: greeting | سلام,درود,hi | سلام داداش!", reply_markup=_back("apanel_offline"))

@router.callback_query(F.data.startswith("apanel_off_del_"))
async def cb_off_del(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    aid = int(cq.data.split("_")[-1])
    await db.delete_offline_answer(aid)
    await cq.answer("✅ حذف شد.", show_alert=True)
    await cb_offline_menu(cq)

# ═══════════════════════════════════════════
# UNANSWERED QUESTIONS
# ═══════════════════════════════════════════

@router.callback_query(F.data == "apanel_unanswered")
async def cb_unanswered(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    unanswered = await db.get_unanswered()
    if not unanswered:
        return await cq.message.edit_text("✅ هیچ سوال بی‌جوابی وجود ندارد.", reply_markup=_back("apanel_back"))
    lines = ["❓ **سوالات بی‌جواب**\n\n"]
    b = InlineKeyboardBuilder()
    for q in unanswered:
        qid = q["id"]
        question = q["question"][:40]
        user_id = q["user_id"]
        lines.append(f"• [{qid}] {question}... (👤 {user_id})")
        b.button(text=f"✅ {qid}", callback_data=f"apanel_unans_done_{qid}")
        b.button(text=f"➕ {qid}", callback_data=f"apanel_unans_add_{qid}")
    b.button(text="🔙 برگشت", callback_data="apanel_back")
    b.adjust(2)
    await cq.message.edit_text("\n".join(lines)[:4000], reply_markup=b.as_markup())

@router.callback_query(F.data.startswith("apanel_unans_done_"))
async def cb_unans_done(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    qid = int(cq.data.split("_")[-1])
    await db.mark_unanswered_done(qid)
    await cq.answer("✅ بررسی شد.", show_alert=True)
    await cb_unanswered(cq)

@router.callback_query(F.data.startswith("apanel_unans_add_"))
async def cb_unans_add(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    qid = int(cq.data.split("_")[-1])
    unanswered = await db.get_unanswered(limit=100)
    q = next((u for u in unanswered if u["id"] == qid), None)
    if not q:
        return await cq.answer("❌ یافت نشد.", show_alert=True)
    _pending[cq.from_user.id] = ("unans_new_intent", qid, q["question"])
    await cq.message.edit_text(
        f"✏️ سوال: `{q['question'][:100]}`\n\n"
        f"**اسم intent رو بفرست** (مثلاً: price, support, vpn)\n\n"
        f"این دسته‌بندی برای پاسخ به این سوال استفاده می‌شه.",
        reply_markup=_back("apanel_unanswered")
    )

# ═══════════════════════════════════════════
# PENDING MESSAGE HANDLER
# ═══════════════════════════════════════════

@router.message(F.text, F.chat.type == "private")
async def pending_handler(message: Message):
    uid = message.from_user.id
    if not _check(uid): return
    text = message.text.strip()

    # ─── PIN Authentication ───
    if uid in _PIN_PENDING:
        _PIN_PENDING.discard(uid)
        remaining = _PIN_MAX_ATTEMPTS - _PIN_ATTEMPTS.get(uid, 0)
        if remaining <= 0:
            return await message.answer(f"⏳ تلاش‌هات تموم شد. {_PIN_COOLDOWN // 60} دقیقه صبر کن.")
        if not text.isdigit() or len(text) < 4 or len(text) > 6:
            _PIN_ATTEMPTS[uid] = _PIN_ATTEMPTS.get(uid, 0) + 1
            remaining -= 1
            if remaining <= 0:
                return await message.answer(f"⏳ تلاش‌هات تموم شد. {_PIN_COOLDOWN // 60} دقیقه صبر کن.")
            _PIN_PENDING.add(uid)
            return await message.answer(f"❌ PIN باید ۴ تا ۶ رقمی باشه. ({remaining} تلاش باقی مونده)")
        pin_hash = await _get_pin_hash()
        if pin_hash and hashlib.sha256(text.encode()).hexdigest() == pin_hash:
            await _save_session(uid)
            _PIN_ATTEMPTS.pop(uid, None)
            return await _show_dashboard(message)
        _PIN_ATTEMPTS[uid] = _PIN_ATTEMPTS.get(uid, 0) + 1
        remaining -= 1
        if remaining <= 0:
            return await message.answer(f"⏳ PIN اشتباه! {_PIN_COOLDOWN // 60} دقیقه صبر کن.")
        _PIN_PENDING.add(uid)
        return await message.answer(f"❌ PIN اشتباه! ({remaining} تلاش باقی مونده)")

    # ─── Regular pending actions ───
    if uid not in _pending: return
    action = _pending.pop(uid)

    try:
        if action == "users_search":
            uid_search = int(text)
            profile = await db.get_user_profile(uid_search)
            if not profile:
                return await message.answer("❌ کاربر پیدا نشد.", reply_markup=_back())
            mem = await db.get_user_memory(uid_search, 0)
            mem_size = len(mem or "")
            groups = await db.get_user_groups_count(uid_search)
            banned = await db.is_banned(0, uid_search)
            status = "🚫 Blocked" if banned else "🟢 Normal"
            first_seen = (profile.get("first_seen") or "نامشخص")[:10]
            last_seen = (profile.get("last_seen") or "نامشخص")[:16]
            ai_count = profile.get("ai_usage_count", 0)
            msg_count = profile.get("message_count", 0)
            b = InlineKeyboardBuilder()
            b.button(text="🚫 بلاک/رفع بلاک", callback_data=f"apanel_block_{uid_search}")
            b.button(text="🧹 پاک کردن حافظه", callback_data=f"apanel_memdo_{uid_search}")
            b.button(text="📜 تاریخچه", callback_data=f"apanel_history_{uid_search}")
            b.button(text="🔙 برگشت", callback_data="apanel_users")
            b.adjust(2)
            await message.answer(
                f"👤 **پروفایل کاربر**\n\n"
                f"🆔 `{uid_search}`\n"
                f"👤 {profile.get('full_name', 'نامشخص')}\n"
                f"🏘 `{groups}` گروه\n"
                f"📝 `{msg_count}` پیام\n"
                f"🤖 `{ai_count}` درخواست AI\n"
                f"🧠 حافظه: `{mem_size}` کاراکتر\n"
                f"📅 عضویت: `{first_seen}`\n"
                f"🕐 آخرین فعالیت: `{last_seen}`\n"
                f"وضعیت: {status}",
                reply_markup=b.as_markup()
            )
            return

        elif isinstance(action, tuple):
            act_type = action[0]

            if act_type == "set":
                key = action[1]
                from config import settings as cfg
                val = int(text) if text.isdigit() else (float(text) if text.replace(".", "").isdigit() else text)
                setattr(cfg, key, val)
                return await message.answer(f"✅ `{key}` = `{val}`", reply_markup=_back("apanel_settings"))

            elif act_type == "add_key":
                provider = action[1]
                pool = {"gemini": gemini_pool, "groq": groq_pool, "openrouter": openrouter_pool, "huggingface": huggingface_pool}.get(provider)
                if pool:
                    try:
                        await db.add_api_key(provider, text)
                        logger.info(f"Admin added key ...{text[-4:]} to {provider} (DB)")
                        await pool.load_from_db()
                        return await message.answer(f"✅ کلید به `{provider}` اضافه و در دیتابیس ذخیره شد.", reply_markup=_back("apanel_keys"))
                    except Exception as e:
                        return await message.answer(f"❌ خطا در ذخیره: {e}", reply_markup=_back())
                return await message.answer("❌ Provider پیدا نشد.", reply_markup=_back())

            elif act_type == "edit_prompt":
                key = action[1]
                try:
                    await db.set_setting(f"custom_{key}_prompt", text)
                    return await message.answer(f"✅ پرامپت `{key}` ذخیره شد.", reply_markup=_back("apanel_prompts"))
                except Exception as e:
                    return await message.answer(f"❌ {e}", reply_markup=_back())

            elif act_type == "gmsg":
                chat_id = int(action[1])
                await message.bot.send_message(chat_id, text)
                return await message.answer("✅ پیام ارسال شد.", reply_markup=_back())

            elif act_type == "offline_new_answer":
                intent = action[1]
                triggers = action[2]
                answer = text.strip()
                await db.add_offline_answer(intent, triggers, answer, priority=2)
                _clear_kb_cache()
                return await message.answer("✅ پاسخ ذخیره شد.", reply_markup=_back("apanel_offline"))

        elif action == "broadcast":
            groups = await db.get_all_groups()
            sent = failed = 0
            for g in groups:
                try:
                    await message.bot.send_message(g["chat_id"], text)
                    sent += 1
                except: failed += 1
            return await message.answer(f"📢 **ارسال شد**\n\n✅ موفق: {sent}\n❌ ناموفق: {failed}", reply_markup=_back())

        elif action == "mem_clear":
            uid_clear = int(text)
            await db.save_user_memory(uid_clear, 0, "")
            return await message.answer(f"✅ حافظه `{uid_clear}` پاک شد.", reply_markup=_back("apanel_memory"))

        elif action == "set_pin":
            if not text.isdigit() or len(text) < 4 or len(text) > 6:
                _pending[uid] = "set_pin"
                return await message.answer("❌ PIN باید ۴ تا ۶ رقمی باشه. دوباره بفرست.")
            await _set_pin_hash(text)
            await _save_session(uid)
            return await _show_dashboard(message)

        elif action == "offline_new_intent":
            parts = text.split("|")
            intent = parts[0].strip()
            triggers = parts[1].strip() if len(parts) > 1 else intent
            answer = parts[2].strip() if len(parts) > 2 else ""
            if not answer:
                _pending[uid] = ("offline_new_answer", intent, triggers)
                return await message.answer("✏️ **متن پاسخ رو بفرست**", reply_markup=_back("apanel_offline"))
            await db.add_offline_answer(intent, triggers, answer, priority=2)
            _clear_kb_cache()
            return await message.answer("✅ پاسخ ذخیره شد.", reply_markup=_back("apanel_offline"))

        elif isinstance(action, tuple) and action[0] == "unans_new_intent":
            qid = action[1]
            question = action[2]
            intent = text.strip()
            if not intent:
                return await message.answer("❌ اسم intent نمی‌تونه خالی باشه.", reply_markup=_back("apanel_unanswered"))
            triggers = question[:200]
            _pending[uid] = ("unans_new_answer", qid, intent, triggers)
            return await message.answer(
                f"✏️ **متن پاسخ رو برای intent `{intent}` بفرست**\n\n"
                f"سوال اصلی: `{question[:100]}`",
                reply_markup=_back("apanel_unanswered")
            )

        elif isinstance(action, tuple) and action[0] == "unans_new_answer":
            qid = action[1]
            intent = action[2]
            triggers = action[3]
            answer = text.strip()
            if not answer:
                return await message.answer("❌ پاسخ نمی‌تونه خالی باشه.", reply_markup=_back())
            await db.add_offline_answer(intent, triggers, answer, priority=2)
            await db.mark_unanswered_done(qid)
            _clear_kb_cache()
            return await message.answer("✅ پاسخ ذخیره و سوال از صف بی‌جواب حذف شد.", reply_markup=_back("apanel_unanswered"))

    except ValueError:
        return await message.answer("❌ آیدی کاربر باید عدد باشه.", reply_markup=_back())
    except Exception as e:
        return await message.answer(f"❌ خطا: {e}", reply_markup=_back())

# ═══════════════════════════════════════════
# CALLBACK HANDLERS
# ═══════════════════════════════════════════

@router.callback_query(F.data.startswith("apanel_block_"))
async def cb_block(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    uid = int(cq.data.split("_")[-1])
    try:
        users = await db.get_all_users()
        groups = [u["chat_id"] for u in users if u.get("user_id") == uid]
        if not groups: groups = [0]
        chat_id = groups[0]
        banned = await db.is_banned(chat_id, uid)
        if banned:
            await db.unban_user(chat_id, uid)
            await cq.answer("✅ رفع بلاک شد.", show_alert=True)
        else:
            await db.ban_user(chat_id, uid, "admin block")
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

@router.callback_query(F.data.startswith("apanel_history_"))
async def cb_user_history(cq: CallbackQuery):
    if not _check(cq.from_user.id): return
    uid = int(cq.data.split("_")[-1])
    try:
        async with db.db.execute(
            "SELECT content, role, created_at FROM chat_history WHERE user_id = ? ORDER BY created_at DESC LIMIT 10",
            (uid,)
        ) as cursor:
            rows = await cursor.fetchall()
        if not rows:
            return await cq.answer("❌ تاریخچه‌ای نیست.", show_alert=True)
        lines = [f"📜 **تاریخچه کاربر `{uid}`**\n"]
        for r in rows:
            role = "👤" if r["role"] == "user" else "🤖"
            lines.append(f"{role} {r['content'][:100]}")
        await cq.message.edit_text("\n".join(lines)[:4000], reply_markup=_back("apanel_users"))
    except Exception as e:
        await cq.answer(f"❌ {e}", show_alert=True)

# ─── Expose stats for recording from other modules ───

def record_request(latency: float = 0):
    _stats.record_request(latency)

def record_error(provider: str, model: str, error: str):
    _stats.record_error(provider, model, error)
