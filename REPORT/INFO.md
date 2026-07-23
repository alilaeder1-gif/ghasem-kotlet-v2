# INFO.md — توضیحات تکمیلی

## اسم بات
- **نام:** کُتلت (تغییرناپذیر)
- **نام‌های مستعار:** کتی، قاسم
- **سازنده:** عمو ترامپ
- **یوزرنیم:** @kotletaiBot

## تکنولوژی‌ها
- **زبان:** Python 3.11
- **فریمورک بات:** aiogram 3
- **پنل مدیریت:** Flask
- **دیتابیس:** SQLite (aiosqlite + sqlite3)
- **کش:** Redis (اختیاری)
- **AI Provider:** Groq (Llama 3.3 70B)
- **جستجو:** DuckDuckGo
- **Host:** Railway (Nixpacks)

## متغیرهای محیطی
| متغیر | توضیح | اجباری |
|-------|-------|--------|
| BOT_TOKEN | توکن ربات تلگرام | ✅ |
| GROQ_API_KEY | کلید API گروک | ✅ |
| ADMIN_IDS | آیدی عددی ادمین‌ها (کاما جدا) | ✅ |
| DATABASE_PATH | مسیر دیتابیس | optional |
| REDIS_URL | آدرس Redis | optional |
| PORT | پورت پنل مدیریت | optional |

## محدودیت‌ها
- Groq: 30 req/min (free tier)
- DuckDuckGo: rate limit نامشخص (reasonable use)
- SQLite: مناسب برای مقیاس کوچک تا متوسط
- Railway: filesystem ephemeral (مگر Volume داشته باشه)
