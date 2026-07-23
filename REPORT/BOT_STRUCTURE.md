# BOT_STRUCTURE.md — معماری بات

## جریان پیام

```
پیام کاربر → Telegram Webhook/Polling
  → aiogram Dispatcher
    → AntiFloodMiddleware (چک flood)
    → group_tracker.track_group (ذخیره گروه + کاربر + ادمین)
    → ai_chat_handler (F.text, ~F.text.startswith("/"))
      ├── 1) چک منشن/ریپلای/اسم/سلام (فقط گروه)
      ├── 2) load persona از دیتابیس
      ├── 3) load chat_history (۶ تبادل آخر)
      ├── 4) load user_memory از دیتابیس
      ├── 5) ask_ai()
      │    ├── a) چک کش Redis
      │    ├── b) _call_deepseek (Groq API)
      │    ├── c) اگر response با SEARCH: شروع شد → web_search() → دوباره call
      │    └── d) کش کردن نتیجه
      ├── 6) ارسال جواب به کاربر
      ├── 7) save_chat به chat_history
      └── 8) extract_memory و save_user_memory
```

## جریان ویس

```
Voice Message → voice_handler
  ├── 1) دریافت فایل از Telegram
  ├── 2) ارسال به Groq Whisper (whisper-large-v3)
  ├── 3) متن استخراج شده
  ├── 4) ask_ai() مثل بالا
  └── 5) Reply با جواب 🎤
```

## جریان پنل مدیریت (جدید — داخلی بات)

```
User → Private Chat → /ghasemkotlet
  ├── /groups — لیست همه گروه‌ها
  ├── /users — لیست کاربران
  ├── /g <chat_id> — جزئیات گروه
  ├── /gmsg <chat_id> <متن> — ارسال پیام
  ├── /ghistory <chat_id> — تاریخچه
  ├── /gtoggle <chat_id> — فعال/غیرفعال AI
  └── /gleave <chat_id> — خروج از گروه
```

## جریان پنل مدیریت (قدیمی — وب، غیرفعال)

```
User → Browser → Railway → Flask (admin_panel.py)
  ├── 1) GET /login → فرم (Telegram ID + Password)
  ├── 2) POST /login (send_code) → ارسال کد به تلگرام
  ├── 3) POST /login (verify) → چک کد + رمز → session
  └── 4) Protected routes (داشبورد، گروه‌ها، کاربران، ...)
```

## دیتابیس

- **موتور:** SQLite با WAL mode
- **دسترسی:** bot.py از aiosqlite (async)، admin_panel.py از sqlite3 (sync)
- **مسیر優先:** /data/bot_data.db > /tmp/bot_data.db > DATABASE_PATH > /app/bot_data.db > bot_data.db
- **WAL mode:** فعال — جلوگیری از قفل شدن بین دو پروسس

## حافظه کاربر

- جدول `user_memory` با کلید `(user_id, chat_id)`
- بعد هر پاسخ AI، extract_memory با Groq خلاصه میگیره
- دفعه بعد حافظه توی پرامپت inject میشه
