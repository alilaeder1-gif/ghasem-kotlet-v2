# REPORT.md — وضعیت کلی پروژه

## پروژه: ربات تلگرام کُتلت (Kotlet AI Bot)
یک ربات گروهی تلگرام با هوش مصنوعی، پنل مدیریت تحت وب، و قابلیت جستجوی اینترنتی.

## وضعیت: فعال ✅
- **Host:** Railway (Nixpacks)
- **Bot Username:** @kotletaiBot
- **AI Provider:** Groq (Llama 3.3 70B) — رایگان، 30 req/min
- **Admin Panel:** Flask + SQLite + Telegram 2FA
- **Database:** SQLite با WAL mode (قابل نصب روی Railway Volume)
- **Search:** DuckDuckGo (رایگان، بدون API Key)

## قابلیت‌های اصلی
- چت هوشمند گروهی با AI (فارسی، محاوره‌ای)
- تشخیص سلام و منشن و ریپلای
- فرمان‌های گروهی (/tag, /game, /guess, /remind, /summary و ...)
- تبدیل ویس به متن (Whisper via Groq)
- جستجوی اینترنتی خودکار (DuckDuckGo)
- حافظه کاربر (ذخیره اطلاعات هر کاربر)
- پنل مدیریت با احراز هویت دو مرحله‌ای تلگرام
- مدیریت گروه‌ها، کاربران، دستورات سفارشی، پاسخ خودکار
- Broadcast به همه گروه‌ها
- مشاهده تاریخچه مکالمات با قابلیت جستجو و فیلتر
- نمایش دیتابیس

## وضعیت کامیت‌ها
- Git: active, main branch
- آخرین کامیت: 749c76f — gitignore + حذف .env.railway از tracking
- Repository: https://github.com/alilaeder1-gif/ghasem-kotlet-v2

## ساختار دیتابیس
14 جدول: welcome_settings, rules, spam_log, banned_users, muted_users, chat_history, ai_persona, custom_commands, auto_replies, bot_groups, group_users, group_settings, panel_config, user_memory
