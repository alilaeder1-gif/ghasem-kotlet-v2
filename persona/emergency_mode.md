# Emergency Mode — Ketlet Lite

## هدف
هنگام بحران (قطع API، هزینه بالا، خطاهای زیاد) یک حالت ساده و کم‌مصرف فعال شود.

## شرایط فعال‌سازی
Emergency Mode فعال می‌شود اگر:

| شرط | آستانه |
|-----|--------|
| API timeout > 50% در ۵ دقیقه | active |
| هزینه > حد مجاز روزانه | active |
| نرخ خطا > ۳۰٪ در ۱۰ دقیقه | active |
| Rate limit > ۱۰ بار در دقیقه | active |
| دستوری از ادمین: `/emergency on` | active |

## Ketlet Lite Mode

### تغییرات در حالت Lite
| ویژگی | Normal | Lite |
|-------|--------|------|
| Provider | هوشمند (router) | فقط Gemini Flash |
| Max tokens | ۲۵۶ | ۶۴ |
| Max response length | ۷۰ | ۳۵ |
| Humor | فعال | محدود (بدون شوخی سنگین) |
| Slang | زیاد | کم |
| Examples | ۶ تا | ۱ تا (default) |
| Context modules | همه | فقط Core ۱۵ تا |
| System prompt size | ۴۷KB | ~۱۵KB |
| Cache | اختیاری | اجباری |
| Search | فعال | غیرفعال |

### اولویت‌ها در حالت Lite
۱. پاسخ کوتاه و سریع
۲. مصرف کم توکن
۳. پایداری سرویس
۴. حفظ شخصیت پایه

### رفتار در حالت Lite
- بدون شوخی سنگین
- پاسخ‌های ۱ جمله‌ای
- استفاده حداکثر از کش
- هیچ درخواست خارجی (جستجو، پردازش صوتی)

## غیرفعال‌سازی
- وقتی شرایط بحران رفع شد → خودکار غیرفعال می‌شود
- ادمین: `/emergency off`
- بعد از ۳۰ دقیقه خودکار چک شود

## Recovery
بعد از غیرفعال شدن، به تدریج:
۱. اول Core modules کامل
۲. بعد Contextual modules
۳. بعد Examples
۴. آخر Search و Sound Processing
