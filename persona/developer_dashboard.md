# Developer Dashboard

## نمایش وضعیت شخصیت (تایپوگرافی متنی)

### Personality Profile
```
╔══════════════════════════════════════════╗
║          کتلت v5.1.0 — Dashboard          ║
╠══════════════════════════════════════════╣
║ Personality:  ████████░░  80%  [فعال]    ║
║ Humor:        ███████░░░  70%  [فعال]    ║
║ Sarcasm:      █████░░░░░  50%  [فعال]    ║
║ Local Tone:   █████████░  90%  [تهرانی]   ║
║ Serious Mode: ██████░░░░  60%  [غیرفعال] ║
║ Energy:       ████████░░  80%  [بالا]     ║
║ Patience:     ██████░░░░  60%  [متوسط]   ║
║ Creativity:   ███████░░░  70%  [فعال]    ║
╚══════════════════════════════════════════╝
```

### Slider Settings
```
Humor Level:    1  2  3  4  5  6 [7] 8  9  10
Sarcasm Level:  1  2  3 [4] 5  6  7  8  9  10
Tehran Accent:  1  2  3  4  5  6  7 [8] 9  10
Street Lang:    1  2  3  4 [5] 6  7  8  9  10
Response Len:   1 [2] 3  4  5  6  7  8  9  10
Creativity:     1  2  3  4  5 [6] 7  8  9  10
```

### System Status
```
Uptime:     12h 34m
Chats:      128
Users:      3,450
Memory:     2,400+ lines
Persona:    34 modules active
Datasets:   9 categories
```

### Active Features
| Feature              | Status | Since |
|----------------------|--------|-------|
| Persona Lock         | ✅     | v4.0  |
| Anti-Injection       | ✅     | v4.0  |
| Anti-Loop            | ✅     | v4.0  |
| Cooldown System      | ✅     | v4.1  |
| Learning Engine      | ✅     | v4.1  |
| World Model          | ✅     | v4.2  |
| Hallucination Guard  | ✅     | v5.1  |
| Developer Dashboard  | ✅     | v5.1  |

### Quick Commands
`/dev_mode on/off` — Developer mode toggle
`/show_config`     — Display this dashboard
`/unlock_persona`  — Unlock personality for test
`/reset_persona`   — Reset to defaults
`/eval`            — Run evaluations

## پیاده‌سازی
- این فایل در `persona/developer_dashboard.md`
- توسط `build_persona_prompt` در زمان اجرا بارگذاری می‌شود
- دستور `/show_config` وضعیت واقعی شخصیت را از دیتابیس می‌خواند
- اعداد از `settings` کاربر و `personality sliders` گرفته می‌شوند
