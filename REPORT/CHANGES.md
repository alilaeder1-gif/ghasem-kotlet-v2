# CHANGES.md — تاریخچه تغییرات

## 2026-07-23 — Admin Bot Panel + Bug Fixes (0f1e023)
- **ادمین پنل داخل بات:** ۸ دستور مدیریتی در پیوی (`/ghasemkotlet`)
- **رفع باگ group_tracker:** هندلر همه پیام‌ها رو میخورد — دستورات کار نمیکردن
- **رفع باگ auto-reply:** `check_auto_replies` همه متن‌ها رو میگرفت — AI کار نمیکرد
- **ادغام auto-reply:** به داخل bot.ai_chat_handler منتقل شد
- **حذف لینک پنل وب:** از همه دستورات پاک شد
- **مدل‌های Groq:** آپدیت شد — ۳ مدل فعال (بقیه decommissioned)
- **SEARCH_INSTRUCTION برگشت:** AI میدونه میتونه سرچ کنه
- **Fallback مدل:** OpenRouter پشتیبان (اگه OPENROUTER_API_KEY ست بشه)
- **ثابت موندن /start:** ریپلای توی گروه، answer توی پیوی
- **دستورات کوتاه:** پرامپت برای جواب یک خطی
- **پرامپت طبیعی:** حذف جونم اضافه — فقط جاهای مناسب
- **misc.router:** تغییر اولویت ثبت برای درست شدن دستورات
- **رفع syntax error:** پرانتز اضافی در DEFAULT_PROMPT (علت کرش Railway)

## 2026-07-23 — Major Fixes (6cd00a5 → 749c76f)
- **پرامپت متعادل شد:** ۵۰٪ شوخ‌طبعی، ۵۰٪ جدی — اولویت با جواب درست
- **رفع باگ جستجو:** نتایج سرچ گرفته میشد ولی به AI داده نمیشد
- **WAL mode فعال:** جلوگیری از قفل شدن دیتابیس بین bot.py و admin_panel.py
- **API Key یکپارچه:** ai_chat.py و bot.py از `config.GROQ_API_KEY` استفاده میکنن
- **init_db.py:** اضافه شدن جدول user_memory و ایندکس chat_history
- **رفع باگ قالب‌ها:** cmd.group_title → cmd.title
- **حذف کاراکتر چینی:** "现在" → "حالا" در custom.py
- **حذف دیباگ پرینت:** "AI_CHAT MODULE LOADED"
- **امنیت:** .env.railway از git خارج شد
- **تمیزی کد:** import تکراری حذف، متغیر بی‌استفاده حذف

## 2026-07-23 — Web Search (ef9a987)
- افزودن جستجوی اینترنتی با DuckDuckGo (رایگان)
- AI تصمیم میگیره کی نیاز به جستجو داره (SEARCH: marker)
- `duckduckgo_search` به requirements اضافه شد

## قبلی — تغییرات اصلی
- تغییر از Gemini → DeepSeek → Groq
- حذف voice response (memory issue)
- افزودن voice transcription (Whisper)
- پنل مدیریت با Telegram 2FA
- Auto-sync گروه‌ها روی هر پیام
- Chat history در دیتابیس
- حافظه کاربر
