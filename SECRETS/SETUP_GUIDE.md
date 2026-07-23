# SETUP_GUIDE.md — راهنمای راه‌اندازی

## پیش‌نیازها
- حساب Railway.app
- توکن ربات (@BotFather)
- کلید Groq (console.groq.com)

## مراحل

### 1. دریافت توکن ربات
- برید به @BotFather
- /newbot
- اسم: کُتلت
- یوزرنیم: kotletaiBot
- توکن رو ذخیره کنید

### 2. دریافت Groq API Key
- برید به https://console.groq.com/keys
- Create API Key
- copy کنید (gsk_...)

### 3. متغیرهای Railway
در Railway Dashboard → Variables:
```
BOT_TOKEN=8593537827:AAG4Wy9SG0Z7FBn8Tj-h2_rdjF7xld4JQak
GROQ_API_KEY=gsk_...
ADMIN_IDS=123456789,987654321
```

### 4. Railway Volume (اختیاری — برای دیتابیس پایدار)
- تب Volumes → New Volume
- Mount Path: /data
- Save

### 5. Deploy
- Fork/Clone repository
- Railway New Project → Deploy from GitHub
- Done!

### 6. BotFather تنظیمات
- /setcommands با لیست botfather-commands.txt
- /setdescription و /setabouttext
- /setprivacy → Disable (برای دیدن همه پیام‌ها)

## عیب‌یابی
- اگه بات جواب نمیده → چک کنید GROQ_API_KEY
- اگه پنل لاگین نمیکنه → ADMIN_IDS رو چک کنید
- اگه دیتا پاک میشه → Railway Volume نصب کنید
