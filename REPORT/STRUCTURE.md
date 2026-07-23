# STRUCTURE.md — ساختار کامل فایل‌ها

```
telegram-bot/
├── bot.py                      # اصلی — Dispatcher، هندلر چت AI و ویس
├── start.py                    # لانچر — bot.py + admin_panel.py رو اجرا میکنه
├── init_db.py                  # دیتابیس رو میسازه (قبل از استارت)
├── admin_panel.py              # پنل مدیریت Flask (ورود با ۲FA تلگرام)
├── database.py                 # کلاس Database — همه کوئری‌های SQLite
├── cache.py                    # کلاس Cache — کش Redis (اختیاری)
├── config.py                   # متغیرهای محیطی (BOT_TOKEN, GROQ_API_KEY, ...)
├── railway.json                # کانفیگ Railway (build + deploy)
├── requirements.txt            # وابستگی‌ها
├── Dockerfile                  # (اختیاری — فقط bot.py رو اجرا میکنه)
├── .gitignore
├── .env                        # توکن‌های محلی (gitignored)
│
├── handlers/
│   ├── ai_chat.py              # DEFAULT_PROMPT، ask_ai، web_search، extract_memory
│   ├── group_tracker.py        # ردیابی گروه‌ها، کاربران، ادمین‌ها، invite link
│   ├── fun.py                  # /tag, /game, /guess, /remind, /summary, /history
│   ├── persona.py              # /setname, /setprompt, /toggleai, /showprompt
│   ├── misc.py                 # /start, /help, /stats, /id
│   ├── admin.py                # دستورات ادمین (بن، میوت، ...)
│   ├── welcome.py              # خوشامدگویی
│   ├── rules.py                # /rules
│   ├── spam.py                 # محافظت اسپم
│   ├── custom.py               # دستورات سفارشی و پاسخ خودکار
│   └── force_sub.py            # عضویت اجباری (disconnected)
│
├── middlewares/
│   └── anti_flood.py           # Anti-Flood middleware
│
├── utils/
│   └── helpers.py              # format_time و توابع کمکی
│
├── templates/                  # قالب‌های Jinja2 پنل مدیریت
│   ├── base.html               # قالب پایه با منوی کناری
│   ├── login.html              # فرم ورود ۲ مرحله‌ای
│   ├── setup.html              # تنظیم اولیه رمز
│   ├── dashboard.html          # داشبورد با آمار
│   ├── groups.html             # لیست گروه‌ها
│   ├── group_detail.html       # جزئیات گروه + کنترل (leave, toggle AI, send, bans, mutes)
│   ├── users.html              # لیست کاربران + ارسال پیام خصوصی
│   ├── ai_settings.html        # تنظیمات AI + فرم ساخت شخصیت
│   ├── commands.html           # دستورات سفارشی
│   ├── auto_replies.html       # پاسخ خودکار + فرم اضافه کردن
│   ├── broadcast.html          # ارسال پیام گروهی
│   ├── chat_history.html       # تاریخچه مکالمات + جستجو
│   ├── database.html           # نمایشگر دیتابیس
│   └── settings.html           # تنظیمات پنل (تغییر رمز)
│
├── REPORT/                     # مستندات پروژه
│   ├── REPORT.md
│   ├── STRUCTURE.md
│   ├── BOT_STRUCTURE.md
│   ├── CHANGES.md
│   ├── INFO.md
│   └── SECURITY.md
│
└── SECRETS/                    # تنظیمات محرمانه (راهنما)
    ├── 01-bot-token.txt
    ├── 02-admin-ids.txt
    ├── 03-api-worker.txt
    ├── 04-master-password.txt
    ├── 05-default-settings.txt
    ├── botfather-commands.txt
    ├── README.txt
    └── SETUP_GUIDE.md
```
