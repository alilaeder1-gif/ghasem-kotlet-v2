# قاسم کتلت - مستندات کامل پروژه

---

## ۱. اکانت‌ها

| سرویس | اکانت | لینک |
|-------|-------|------|
| **GitHub** | alilaeder1-gif | https://github.com/alilaeder1-gif |
| **Railway** | alilaeder1-gif (GitHub login) | https://railway.app |
| **HuggingFace** | alilaeder1-gif | https://huggingface.co |
| **Telegram** | @whatcore_bot | https://t.me/whatcore_bot |

---

## ۲. سکرت‌ها

> مقادیر واقعی در فایل `.env` هستند (در گیت push نمی‌شوند).
> برای Railway این مقادیر را در **Variables** تنظیم کنید.

| متغیر | توضیح | منبع |
|-------|-------|------|
| `BOT_TOKEN` | توکن ربات تلگرام | @BotFather |
| `HUGGINGFACE_API_KEY` | کلید API HuggingFace | huggingface.co/settings/tokens |
| `PANEL_PASSWORD` | رمز پنل ادمین | `admin123` (اولین بار تغییر بدید) |

### مدل AI:
```
AI_MODEL = meta-llama/Llama-3-8B-Instruct
```

---

## ۳. سرورها

### Railway (Production):
| مشخصه | مقدار |
|-------|-------|
| **پلتفرم** | Railway.app |
| **آدرس پنل** | https://ghasem-kotlet-v2.up.railway.app |
| **پورت** | 8080 (توسط Railway تنظیم می‌شود) |
| **دیتابیس** | `/app/data/bot_data.db` (SQLite) |
| **Redis** | Plugin Railway (اختیاری) |
| **Logs** | Railway Dashboard → Deployments → Logs |

### محلی (Local Development):
| مشخصه | مقدار |
|-------|-------|
| **مسیر** | `E:\DNS.Jumper.2.2\telegram-bot\` |
| **پنل ادمین** | http://localhost:5001 |
| **دیتابیس** | `bot_data.db` |

---

## ۴. رپو گیتهاب

| مشخصه | مقدار |
|-------|-------|
| **URL** | https://github.com/alilaeder1-gif/ghasem-kotlet-v2 |
| **شاخه اصلی** | `main` |
| **دسترسی** | عمومی |

---

## ۵. ساختار پروژه

```
telegram-bot/
├── bot.py              # ربات تلگرام (aiogram 3)
├── admin_panel.py      # پنل مدیریت وب (Flask)
├── start.py            # اجرای همزمان ربات + پنل
├── init_db.py          # مقداردهی اولیه دیتابیس
├── config.py           # تنظیمات از .env
├── database.py         # کلاس دیتابیس SQLite
├── cache.py            # کش Redis (اختیاری)
├── requirements.txt    # وابستگی‌ها
├── Dockerfile          # داکر فایل
├── railway.json        # تنظیمات Railway
│
├── handlers/           # هندلرهای ربات
│   ├── admin.py        # بن/کیک/میوت/پین
│   ├── welcome.py      # خوشامدگویی خودکار
│   ├── rules.py        # قوانین گروه
│   ├── spam.py         # تشخیص و حذف اسپم
│   ├── ai_chat.py      # چت هوشمند با HuggingFace
│   ├── custom.py       # دستورات سفارشی
│   ├── persona.py      # شخصیت هوش مصنوعی
│   ├── group_tracker.py# ردیابی گروه‌ها و کاربران
│   ├── force_sub.py    # عضویت اجباری کانال
│   └── misc.py         # دستورات متفرقه
│
├── middlewares/
│   └── anti_flood.py   # جلوگیری از flood
│
├── templates/          # قالب‌های پنل ادمین
│   ├── base.html
│   ├── login.html
│   ├── setup.html
│   ├── dashboard.html
│   ├── groups.html
│   ├── group_detail.html
│   ├── users.html
│   ├── commands.html
│   ├── auto_replies.html
│   ├── ai_settings.html
│   ├── broadcast.html
│   ├── database.html
│   └── settings.html
│
└── utils/
    └── helpers.py
```

---

## ۶. دیتابیس (SQLite)

| جدول | توضیح |
|------|-------|
| `welcome_settings` | تنظیمات خوشامدگویی هر گروه |
| `rules` | قوانین هر گروه |
| `spam_log` | لاگ پیام‌های اسپم |
| `banned_users` | کاربران بن شده |
| `muted_users` | کاربران میوت شده |
| `chat_history` | تاریخچه چت با هوش مصنوعی |
| `ai_persona` | شخصیت هوش مصنوعی هر گروه |
| `custom_commands` | دستورات سفارشی ادمین‌ها |
| `auto_replies` | پاسخ‌های خودکار |
| `bot_groups` | گروه‌هایی که ربات عضو است |
| `group_users` | کاربران هر گروه |
| `group_settings` | تنظیمات اختصاصی هر گروه |
| `panel_config` | تنظیمات پنل ادمین |

---

## ۷. API‌های استفاده شده

| API | آدرس | کاربرد |
|-----|------|--------|
| **HuggingFace Inference** | `https://api-inference.huggingface.co/models/{MODEL}` | چت هوش مصنوعی |
| **Telegram Bot API** | `https://api.telegram.org/bot{TOKEN}/{METHOD}` | ارسال/دریافت پیام |

---

## ۸. دستورات ربات

### مدیریت گروه:
| دستور | توضیح | دسترسی |
|-------|-------|--------|
| `/ban` | بن کاربر (با ریپلای) | ادمین |
| `/unban` | آنب بن کاربر | ادمین |
| `/kick` | کیک کاربر از گروه | ادمین |
| `/mute` | میوت کاربر | ادمین |
| `/unmute` | آنمیوت کاربر | ادمین |
| `/pin` | پین کردن پیام | ادمین |
| `/setrules` | تنظیم قوانین گروه | ادمین |
| `/setwelcome` | تنظیم پیام خوشامدگویی | ادمین |
| `/forcesub` | عضویت اجباری در کانال | ادمین |

### شخصی‌سازی هوش مصنوعی:
| دستور | توضیح |
|-------|-------|
| `/setname` | تغییر اسم هوش مصنوعی |
| `/setprompt` | تغییر شخصیت هوش مصنوعی |
| `/toggleai` | فعال/غیرفعال کردن AI |
| `/showprompt` | نمایش تنظیمات فعلی |
| `/aiexamples` | مثال‌های پرامپت |

### دستورات سفارشی:
| دستور | توضیح |
|-------|-------|
| `/setcmd` | ساخت دستور سفارشی جدید |
| `/delcmd` | حذف دستور سفارشی |
| `/listcmds` | لیست دستورات سفارشی |
| `/setreply` | تنظیم پاسخ خودکار |
| `/delreply` | حذف پاسخ خودکار |
| `/listreplies` | لیست پاسخ‌های خودکار |

### عمومی و مدیریت کل:
| دستور | توضیح | دسترسی |
|-------|-------|--------|
| `/start` | شروع ربات | همه |
| `/help` | راهنما | همه |
| `/rules` | نمایش قوانین | همه |
| `/stats` | آمار گروه | همه |
| `/userinfo` | اطلاعات کاربر | همه |
| `/mygroups` | لیست گروه‌ها | ادمین کل |
| `/groupstats` | آمار کامل گروه | ادمین کل |
| `/broadcast` | ارسال پیام به همه گروه‌ها | ادمین کل |

---

## ۹. پنل ادمین

| آدرس | بخش | توضیح |
|------|-----|-------|
| `/` | داشبورد | آمار کلی پروژه |
| `/groups` | گروه‌ها | لیست همه گروه‌ها |
| `/group/{id}` | جزئیات گروه | کاربران، تنظیمات، دستورات |
| `/users` | کاربران | لیست همه کاربران |
| `/ai-settings` | تنظیمات AI | مدیریت شخصیت هر گروه |
| `/commands` | دستورات سفارشی | مشاهده همه دستورات |
| `/auto-replies` | پاسخ خودکار | مشاهده همه پاسخ‌ها |
| `/broadcast` | ارسال پیام | ارسال به همه گروه‌ها |
| `/database` | دیتابیس | مشاهده مستقیم دیتابیس |
| `/settings` | تنظیمات | تغییر رمز پنل |

---

## ۱۰. دیپلوی Railway

### متغیرهای محیطی (اجباری):
| متغیر | مقدار |
|-------|-------|
| `BOT_TOKEN` | از .env |
| `HUGGINGFACE_API_KEY` | از .env |
| `DATABASE_PATH` | `/app/data/bot_data.db` |

### متغیرهای اختیاری:
| متغیر | مقدار پیش‌فرض | توضیح |
|-------|---------------|-------|
| `AI_MODEL` | `meta-llama/Llama-3-8B-Instruct` | مدل AI |
| `REDIS_URL` | `-` | Redis (از Plugin) |
| `SPAM_THRESHOLD` | `5` | تعداد اسپم برای بن |
| `FLOOD_THRESHOLD` | `3` | تعداد پیام برای flood |

### مراحل دیپلوی:
1. اتصال GitHub به Railway
2. انتخاب رپو `ghasem-kotlet-v2`
3. تنظیم متغیرهای محیطی
4. دیپلوی
5. (اختیاری) افزودن Redis Plugin

### لاگ موفق:
```
Database initialized: /app/data/bot_data.db
All tables created successfully!
پایگاه داده متصل شد.
ربات شروع به کار کرد!
```

---

## ۱۱. عیب‌یابی

| مشکل | راه‌حل |
|------|--------|
| `unable to open database file` | Railway Volume رو چک کن، دوباره دیپلوی کن |
| `Conflict: terminated by other getUpdates` | فقط یک نمونه ربات اجرا باشه |
| مدل HuggingFace لود نمیشه | اولین بار ۱-۲ دقیقه طول میکشه |
| پنل ادمین کار نمیکنه | Railway URL رو چک کن |
| Redis وصل نمیشه | Redis Plugin رو اضافه کن |

---

## ۱۲. اطلاعات کلی

| مشخصه | مقدار |
|-------|-------|
| **نام پروژه** | قاسم کتلت |
| **نوع** | ربات مدیریت گروه تلگرام |
| **زبان** | Python 3.11 |
| **فریم‌ورک ربات** | aiogram 3 |
| **فریم‌ورک پنل** | Flask |
| **دیتابیس** | SQLite |
| **کش** | Redis (اختیاری) |
| **هوش مصنوعی** | HuggingFace Inference API |
| **هاست** | Railway.app |
| **گیتهاب** | alilaeder1-gif/ghasem-kotlet-v2 |
| **ربات تلگرام** | @whatcore_bot |
| **آیدی عددی ربات** | 8921796051 |
