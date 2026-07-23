# REPORT.md — وضعیت کلی پروژه

## پروژه: ربات تلگرام کُتلت (Kotlet AI Bot)
یک ربات گروهی تلگرام با هوش مصنوعی، پنل مدیریت داخلی تلگرام، و قابلیت جستجوی اینترنتی.

## وضعیت: فعال ✅
- **Host:** Railway (Nixpacks)
- **Bot Username:** @kotletaiBot
- **AI Provider:** Groq (Llama-3.3-70b-versatile, Llama-3.1-8b-instant, Llama3-8b-8192) + OpenRouter fallback
- **Admin Panel:** داخلی در خود بات (Telegram commands) — بدون پنل وب
- **Database:** SQLite با WAL mode (قابل نصب روی Railway Volume)
- **Search:** DuckDuckGo (رایگان، بدون API Key)

## قابلیت‌های اصلی
- چت هوشمند گروهی با AI (فارسی، محاوره‌ای، یک خطی)
- تشخیص سلام و منشن و ریپلای
- فرمان‌های گروهی (/tag, /game, /guess, /remind, /summary و ...)
- تبدیل ویس به متن (Whisper via Groq)
- جستجوی اینترنتی خودکار (DuckDuckGo)
- حافظه کاربر (ذخیره اطلاعات هر کاربر)
- پنل مدیریت داخلی بات (`/ghasemkotlet`) — ۸ دستور مدیریتی
- مدیریت گروه‌ها، کاربران، دستورات سفارشی، پاسخ خودکار
- Broadcast به همه گروه‌ها
- Fallback خودکار بین ۳ مدل Groq + ۴ مدل OpenRouter
- مشاهده تاریخچه مکالمات

## وضعیت کامیت‌ها
- Git: active, main branch
- آخرین کامیت: 0f1e023 — fix admin_bot
- Repository: https://github.com/alilaeder1-gif/ghasem-kotlet-v2

## ساختار دیتابیس
14 جدول: welcome_settings, rules, spam_log, banned_users, muted_users, chat_history, ai_persona, custom_commands, auto_replies, bot_groups, group_users, group_settings, panel_config, user_memory
