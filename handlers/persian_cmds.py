import re
from aiogram import Router, F
from aiogram.types import Message

router = Router()

# فقط دستورات عمومی (بدون دستورات ادمین پنل)
PERSIAN_MAP = {
    "شروع": "start", "راهنما": "help", "آمار": "stats",
    "آیدی": "id", "نقاشی": "draw", "بکش": "draw", "کد": "code",
    "خلاصه": "summary", "بازی": "game",
    "حدس": "guess", "کلمه": "guessword", "حدس‌کلمه": "guessword",
    "توقف": "stopgame", "بس": "stopgame",
    "یادآور": "remind", "یادآوری": "remind",
    "یادآوری‌ها": "reminders", "تاریخچه": "history",
    "قوانین": "rules", "قانون": "rules",
    "قانون جدید": "setrules", "تنظیم قانون": "setrules",
    "حذف قوانین": "clearrules", "پاک قانون": "clearrules",
    "خوشامد": "setwelcome", "تست خوشامد": "testwelcome",
    "اسم": "setname", "نام": "setname",
    "پرامپت": "setprompt", "هوش": "toggleai",
    "نمایش پرامپت": "showprompt", "مثال": "aiexamples",
    "دستور": "setcmd", "حذف دستور": "delcmd",
    "دستورات": "listcmds",
    "پاسخ": "setreply", "حذف پاسخ": "delreply",
    "پاسخ‌ها": "listreplies",
    "همگام": "sync", "گروه‌های من": "mygroups",
    "پیام همگانی": "broadcast",
    "آمار گروه": "groupstats", "اطلاعات کاربر": "userinfo",
    "اجباری": "forcesub", "بررسی": "checksub",
    "اخطار": "warn", "حذف اخطار": "delwarn", "اخطارها": "warns",
    "ساکت": "mute", "آنمیت": "unmute",
    "تنظیمات": "settings",
}

_keys = sorted(PERSIAN_MAP.keys(), key=len, reverse=True)
PERSIAN_RE = re.compile(r"^(?:" + "|".join(re.escape(k) for k in _keys) + r")(?:\s|$)", re.IGNORECASE)


@router.message(F.text, ~F.text.startswith("/"))
async def persian_handler(message: Message):
    text = message.text.strip()
    m = PERSIAN_RE.match(text)
    if not m:
        return
    persian_cmd = m.group(0).strip()
    eng_cmd = PERSIAN_MAP.get(persian_cmd)
    if not eng_cmd:
        return
    rest = text[m.end():]
    # rewrite message.text to /command so normal handlers can process it
    # aiogram 3 Message uses frozen pydantic — bypass with object.__setattr__
    new_text = f"/{eng_cmd}{ ' ' + rest if rest else ''}"
    object.__setattr__(message, 'text', new_text)
